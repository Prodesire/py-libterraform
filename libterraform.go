package main

import (
	"encoding/json"
	"fmt"
	"github.com/hashicorp/go-plugin"
	"github.com/hashicorp/terraform-svchost/disco"
	backendInit "github.com/hashicorp/terraform/internal/backend/init"
	"github.com/hashicorp/terraform/internal/command/cliconfig"
	"github.com/hashicorp/terraform/internal/command/format"
	"github.com/hashicorp/terraform/internal/didyoumean"
	"github.com/hashicorp/terraform/internal/httpclient"
	"github.com/hashicorp/terraform/internal/logging"
	"github.com/hashicorp/terraform/internal/terminal"
	"github.com/hashicorp/terraform/version"
	"github.com/mitchellh/cli"
	"github.com/mitchellh/colorstring"
	"log"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"unsafe"

	"github.com/hashicorp/terraform/internal/configs"
	"github.com/hashicorp/terraform/internal/experiments"
)

/*
   #include <stdlib.h>
*/
import "C"

// **********************************************
// CLI
// **********************************************

//export RunCli
func RunCli(cArgc C.int, cArgv **C.char, cStdOutFd C.int, cStdErrFd C.int) C.int {
	defer logging.PanicHandler()

	var err error

	// Convert C variables to Go variables
	os.Args = os.Args[:0]
	os.Args = append(os.Args, "Terraform")
	argc := int(cArgc)
	slice := unsafe.Slice(cArgv, argc)
	for _, s := range slice {
		arg := C.GoString(s)
		os.Args = append(os.Args, arg)
	}

	// Override stdout and stdin by given std fd
	origStdout := os.Stdout
	origStderr := os.Stderr
	Stdout := os.NewFile(uintptr(cStdOutFd), "libterraform/pipe/stdout")
	Stderr := os.NewFile(uintptr(cStdErrFd), "libterraform/pipe/stderr")
	os.Stdout = Stdout
	os.Stderr = Stderr
	Ui = &ui{&cli.BasicUi{
		Writer:      Stdout,
		ErrorWriter: Stderr,
		Reader:      os.Stdin,
	}}

	defer func() {
		os.Stdout = origStdout
		os.Stderr = origStderr
		Stdout.Close()
		Stderr.Close()
		runtime.GC()
	}()

	tmpLogPath := os.Getenv(envTmpLogPath)
	if tmpLogPath != "" {
		f, err := os.OpenFile(tmpLogPath, os.O_RDWR|os.O_APPEND, 0666)
		if err == nil {
			defer f.Close()

			log.Printf("[DEBUG] Adding temp file log sink: %s", f.Name())
			logging.RegisterSink(f)
		} else {
			log.Printf("[ERROR] Could not open temp log file: %v", err)
		}
	}

	log.Printf(
		"[INFO] Terraform version: %s %s",
		Version, VersionPrerelease)
	log.Printf("[INFO] Go runtime version: %s", runtime.Version())
	log.Printf("[INFO] CLI args: %#v", os.Args)

	streams, err := terminal.Init()
	if err != nil {
		Ui.Error(fmt.Sprintf("Failed to configure the terminal: %s", err))
		return 1
	}
	if streams.Stdout.IsTerminal() {
		log.Printf("[TRACE] Stdout is a terminal of width %d", streams.Stdout.Columns())
	} else {
		log.Printf("[TRACE] Stdout is not a terminal")
	}
	if streams.Stderr.IsTerminal() {
		log.Printf("[TRACE] Stderr is a terminal of width %d", streams.Stderr.Columns())
	} else {
		log.Printf("[TRACE] Stderr is not a terminal")
	}
	if streams.Stdin.IsTerminal() {
		log.Printf("[TRACE] Stdin is a terminal")
	} else {
		log.Printf("[TRACE] Stdin is not a terminal")
	}

	// NOTE: We're intentionally calling LoadConfig _before_ handling a possible
	// -chdir=... option on the command line, so that a possible relative
	// path in the TERRAFORM_CONFIG_FILE environment variable (though probably
	// ill-advised) will be resolved relative to the true working directory,
	// not the overridden one.
	config, diags := cliconfig.LoadConfig()

	if len(diags) > 0 {
		// Since we haven't instantiated a command.Meta yet, we need to do
		// some things manually here and use some "safe" defaults for things
		// that command.Meta could otherwise figure out in smarter ways.
		Ui.Error("There are some problems with the CLI configuration:")
		for _, diag := range diags {
			earlyColor := &colorstring.Colorize{
				Colors:  colorstring.DefaultColors,
				Disable: true, // Disable color to be conservative until we know better
				Reset:   true,
			}
			// We don't currently have access to the source code cache for
			// the parser used to load the CLI config, so we can't show
			// source code snippets in early diagnostics.
			Ui.Error(format.Diagnostic(diag, nil, earlyColor, 78))
		}
		if diags.HasErrors() {
			Ui.Error("As a result of the above problems, Terraform may not behave as intended.\n\n")
			// We continue to run anyway, since Terraform has reasonable defaults.
		}
	}

	// Get any configured credentials from the config and initialize
	// a service discovery object. The slightly awkward predeclaration of
	// disco is required to allow us to pass untyped nil as the creds source
	// when creating the source fails. Otherwise we pass a typed nil which
	// breaks the nil checks in the disco object
	var services *disco.Disco
	credsSrc, err := credentialsSource(config)
	if err == nil {
		services = disco.NewWithCredentialsSource(credsSrc)
	} else {
		// Most commands don't actually need credentials, and most situations
		// that would get us here would already have been reported by the config
		// loading above, so we'll just log this one as an aid to debugging
		// in the unlikely event that it _does_ arise.
		log.Printf("[WARN] Cannot initialize remote host credentials manager: %s", err)
		// passing (untyped) nil as the creds source is okay because the disco
		// object checks that and just acts as though no credentials are present.
		services = disco.NewWithCredentialsSource(nil)
	}
	services.SetUserAgent(httpclient.TerraformUserAgent(version.String()))

	providerSrc, diags := providerSource(config.ProviderInstallation, services)
	if len(diags) > 0 {
		Ui.Error("There are some problems with the provider_installation configuration:")
		for _, diag := range diags {
			earlyColor := &colorstring.Colorize{
				Colors:  colorstring.DefaultColors,
				Disable: true, // Disable color to be conservative until we know better
				Reset:   true,
			}
			Ui.Error(format.Diagnostic(diag, nil, earlyColor, 78))
		}
		if diags.HasErrors() {
			Ui.Error("As a result of the above problems, Terraform's provider installer may not behave as intended.\n\n")
			// We continue to run anyway, because most commands don't do provider installation.
		}
	}
	providerDevOverrides := providerDevOverrides(config.ProviderInstallation)

	// The user can declare that certain providers are being managed on
	// Terraform's behalf using this environment variable. This is used
	// primarily by the SDK's acceptance testing framework.
	unmanagedProviders, err := parseReattachProviders(os.Getenv("TF_REATTACH_PROVIDERS"))
	if err != nil {
		Ui.Error(err.Error())
		return 1
	}

	// Initialize the backends.
	backendInit.Init(services)

	// Get the command line args.
	binName := filepath.Base(os.Args[0])
	args := os.Args[1:]

	originalWd, err := os.Getwd()
	if err != nil {
		// It would be very strange to end up here
		Ui.Error(fmt.Sprintf("Failed to determine current working directory: %s", err))
		return 1
	}

	// The arguments can begin with a -chdir option to ask Terraform to switch
	// to a different working directory for the rest of its work. If that
	// option is present then extractChdirOption returns a trimmed args with that option removed.
	overrideWd, args, err := extractChdirOption(args)
	if err != nil {
		Ui.Error(fmt.Sprintf("Invalid -chdir option: %s", err))
		return 1
	}
	if overrideWd != "" {
		err := os.Chdir(overrideWd)
		if err != nil {
			Ui.Error(fmt.Sprintf("Error handling -chdir option: %s", err))
			return 1
		}
	}

	// Commands get to hold on to the original working directory here,
	// in case they need to refer back to it for any special reason, though
	// they should primarily be working with the override working directory
	// that we've now switched to above.
	initCommands(originalWd, streams, config, services, providerSrc, providerDevOverrides, unmanagedProviders)

	// Run checkpoint
	go runCheckpoint(config)

	// Make sure we clean up any managed plugins at the end of this
	defer plugin.CleanupClients()

	// Build the CLI so far, we do this so we can query the subcommand.
	cliRunner := &cli.CLI{
		Args:       args,
		Commands:   Commands,
		HelpFunc:   helpFunc,
		HelpWriter: os.Stdout,
	}

	// Prefix the args with any args from the EnvCLI
	args, err = mergeEnvArgs(EnvCLI, cliRunner.Subcommand(), args)
	if err != nil {
		Ui.Error(err.Error())
		return 1
	}

	// Prefix the args with any args from the EnvCLI targeting this command
	suffix := strings.Replace(strings.Replace(
		cliRunner.Subcommand(), "-", "_", -1), " ", "_", -1)
	args, err = mergeEnvArgs(
		fmt.Sprintf("%s_%s", EnvCLI, suffix), cliRunner.Subcommand(), args)
	if err != nil {
		Ui.Error(err.Error())
		return 1
	}

	// We shortcut "--version" and "-v" to just show the version
	for _, arg := range args {
		if arg == "-v" || arg == "-version" || arg == "--version" {
			newArgs := make([]string, len(args)+1)
			newArgs[0] = "version"
			copy(newArgs[1:], args)
			args = newArgs
			break
		}
	}

	// Rebuild the CLI with any modified args.
	log.Printf("[INFO] CLI command args: %#v", args)
	cliRunner = &cli.CLI{
		Name:       binName,
		Args:       args,
		Commands:   Commands,
		HelpFunc:   helpFunc,
		HelpWriter: os.Stdout,

		Autocomplete:          true,
		AutocompleteInstall:   "install-autocomplete",
		AutocompleteUninstall: "uninstall-autocomplete",
	}

	// Before we continue we'll check whether the requested command is
	// actually known. If not, we might be able to suggest an alternative
	// if it seems like the user made a typo.
	// (This bypasses the built-in help handling in cli.CLI for the situation
	// where a command isn't found, because it's likely more helpful to
	// mention what specifically went wrong, rather than just printing out
	// a big block of usage information.)

	// Check if this is being run via shell auto-complete, which uses the
	// binary name as the first argument and won't be listed as a subcommand.
	autoComplete := os.Getenv("COMP_LINE") != ""

	if cmd := cliRunner.Subcommand(); cmd != "" && !autoComplete {
		// Due to the design of cli.CLI, this special error message only works
		// for typos of top-level commands. For a subcommand typo, like
		// "terraform state posh", cmd would be "state" here and thus would
		// be considered to exist, and it would print out its own usage message.
		if _, exists := Commands[cmd]; !exists {
			suggestions := make([]string, 0, len(Commands))
			for name := range Commands {
				suggestions = append(suggestions, name)
			}
			suggestion := didyoumean.NameSuggestion(cmd, suggestions)
			if suggestion != "" {
				suggestion = fmt.Sprintf(" Did you mean %q?", suggestion)
			}
			fmt.Fprintf(os.Stderr, "Terraform has no command named %q.%s\n\nTo see all of Terraform's top-level commands, run:\n  terraform -help\n\n", cmd, suggestion)
			return 1
		}
	}

	exitCode, err := cliRunner.Run()
	if err != nil {
		Ui.Error(fmt.Sprintf("Error executing CLI: %s", err.Error()))
		return 1
	}

	// if we are exiting with a non-zero code, check if it was caused by any
	// plugins crashing
	if exitCode != 0 {
		for _, panicLog := range logging.PluginPanics() {
			Ui.Error(panicLog)
		}
	}
	return C.int(exitCode)
}

// **********************************************
// Config
// **********************************************

// ShortModule is a container for a set of configuration constructs that are
// evaluated within a common namespace.
// Compared with module, there are fewer non-serializable fields.
type ShortModule struct {
	SourceDir string

	CoreVersionConstraints []configs.VersionConstraint

	ActiveExperiments experiments.Set

	Backend              *configs.Backend
	CloudConfig          *configs.CloudConfig
	ProviderConfigs      map[string]*configs.Provider
	ProviderRequirements *configs.RequiredProviders

	Variables map[string]*configs.Variable
	Locals    map[string]*configs.Local
	Outputs   map[string]*configs.Output

	ModuleCalls map[string]*configs.ModuleCall

	ManagedResources map[string]*configs.Resource
	DataResources    map[string]*configs.Resource

	Moved []*configs.Moved
}

func convertModule(mod *configs.Module) *ShortModule {
	shortMod := &ShortModule{
		SourceDir:              mod.SourceDir,
		CoreVersionConstraints: mod.CoreVersionConstraints,
		ActiveExperiments:      mod.ActiveExperiments,
		Backend:                mod.Backend,
		CloudConfig:            mod.CloudConfig,
		ProviderRequirements:   mod.ProviderRequirements,
		Variables:              mod.Variables,
		Locals:                 mod.Locals,
		Outputs:                mod.Outputs,
		ModuleCalls:            mod.ModuleCalls,
		ManagedResources:       mod.ManagedResources,
		DataResources:          mod.DataResources,
		Moved:                  mod.Moved,
	}
	return shortMod
}

//export ConfigLoadConfigDir
func ConfigLoadConfigDir(cPath *C.char) (cMod *C.char, cDiags *C.char, cError *C.char) {
	defer func() {
		recover()
	}()

	parser := configs.NewParser(nil)
	path := C.GoString(cPath)
	mod, diags := parser.LoadConfigDir(path)
	modBytes, err := json.Marshal(convertModule(mod))
	if err != nil {
		cMod = C.CString("")
		cDiags = C.CString("")
		cError = C.CString(err.Error())
		return cMod, cDiags, cError
	}
	diagsBytes, err := json.Marshal(diags)
	if err != nil {
		cMod = C.CString(string(modBytes))
		cDiags = C.CString("")
		cError = C.CString(err.Error())
		return cMod, cDiags, cError
	}
	cMod = C.CString(string(modBytes))
	cDiags = C.CString(string(diagsBytes))
	cError = C.CString("")
	return cMod, cDiags, cError
}

// **********************************************
// Utils
// **********************************************

//export Free
func Free(cString *int) {
	C.free(unsafe.Pointer(cString))
}
