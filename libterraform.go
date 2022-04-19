package main

import (
	"encoding/json"
	"fmt"
	"github.com/hashicorp/go-plugin"
	svchost "github.com/hashicorp/terraform-svchost"
	"github.com/hashicorp/terraform-svchost/disco"
	"github.com/hashicorp/terraform/internal/addrs"
	backendInit "github.com/hashicorp/terraform/internal/backend/init"
	"github.com/hashicorp/terraform/internal/command"
	"github.com/hashicorp/terraform/internal/command/cliconfig"
	"github.com/hashicorp/terraform/internal/command/format"
	"github.com/hashicorp/terraform/internal/command/views"
	"github.com/hashicorp/terraform/internal/command/webbrowser"
	"github.com/hashicorp/terraform/internal/configs"
	"github.com/hashicorp/terraform/internal/didyoumean"
	"github.com/hashicorp/terraform/internal/experiments"
	"github.com/hashicorp/terraform/internal/getproviders"
	"github.com/hashicorp/terraform/internal/httpclient"
	"github.com/hashicorp/terraform/internal/logging"
	"github.com/hashicorp/terraform/internal/terminal"
	"github.com/hashicorp/terraform/version"
	"github.com/mitchellh/cli"
	"github.com/mitchellh/colorstring"
	"log"
	"os"
	"os/signal"
	"path/filepath"
	"runtime"
	"strings"
	"unsafe"
)

/*
   #include <stdlib.h>
*/
import "C"

// **********************************************
// CLI
// **********************************************

var shutdownChs = make(map[chan struct{}]struct{})
var logFile *os.File
var origStdout = os.Stdout
var origStderr = os.Stderr

func init() {
	signalCh := make(chan os.Signal, 4)
	signal.Notify(signalCh, ignoreSignals...)
	signal.Notify(signalCh, forwardSignals...)
	go func() {
		for {
			<-signalCh
			log.Printf("[INFO] Received signal, shutting down")
			for shutdownCh := range shutdownChs {
				shutdownCh <- struct{}{}
			}
			log.Printf("[INFO] Received signal, shut down success")
		}
	}()
}

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
		if len(checkpointResult) > 0 {
			<-checkpointResult
		}
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

	shutdownCh := make(chan struct{}, 2)
	shutdownChs[shutdownCh] = struct{}{}
	defer func() {
		delete(shutdownChs, shutdownCh)
		close(shutdownCh)
	}()
	meta := NewMeta(originalWd, streams, config, services, providerSrc, providerDevOverrides, unmanagedProviders, shutdownCh)
	commands := NewCommands(meta)

	// Run checkpoint
	go runCheckpoint(config)

	// Make sure we clean up any managed plugins at the end of this
	defer func() {
		plugin.CleanupAndRemoveClients()
	}()

	// Build the CLI so far, we do this so we can query the subcommand.
	cliRunner := &cli.CLI{
		Args:       args,
		Commands:   commands,
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
		Commands:   commands,
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
		if _, exists := commands[cmd]; !exists {
			suggestions := make([]string, 0, len(commands))
			for name := range commands {
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

func NewMeta(
	originalWorkingDir string,
	streams *terminal.Streams,
	config *cliconfig.Config,
	services *disco.Disco,
	providerSrc getproviders.Source,
	providerDevOverrides map[addrs.Provider]getproviders.PackageLocalDir,
	unmanagedProviders map[addrs.Provider]*plugin.ReattachConfig,
	shutdownCh <-chan struct{},
) command.Meta {
	var inAutomation bool
	if v := os.Getenv(runningInAutomationEnvName); v != "" {
		inAutomation = true
	}

	for userHost, hostConfig := range config.Hosts {
		host, err := svchost.ForComparison(userHost)
		if err != nil {
			// We expect the config was already validated by the time we get
			// here, so we'll just ignore invalid hostnames.
			continue
		}
		services.ForceHostServices(host, hostConfig.Services)
	}

	configDir, err := cliconfig.ConfigDir()
	if err != nil {
		configDir = "" // No config dir available (e.g. looking up a home directory failed)
	}

	wd := WorkingDir(originalWorkingDir, os.Getenv("TF_DATA_DIR"))

	meta := command.Meta{
		WorkingDir: wd,
		Streams:    streams,
		View:       views.NewView(streams).SetRunningInAutomation(inAutomation),

		Color:            true,
		GlobalPluginDirs: globalPluginDirs(),
		Ui:               Ui,

		Services:        services,
		BrowserLauncher: webbrowser.NewNativeLauncher(),

		RunningInAutomation: inAutomation,
		CLIConfigDir:        configDir,
		PluginCacheDir:      config.PluginCacheDir,

		ShutdownCh: shutdownCh,

		ProviderSource:       providerSrc,
		ProviderDevOverrides: providerDevOverrides,
		UnmanagedProviders:   unmanagedProviders,
	}
	return meta
}

func NewCommands(meta command.Meta) map[string]cli.CommandFactory {

	// The command list is included in the terraform -help
	// output, which is in turn included in the docs at
	// website/docs/cli/commands/index.html.markdown; if you
	// add, remove or reclassify commands then consider updating
	// that to match.

	commands := map[string]cli.CommandFactory{
		"apply": func() (cli.Command, error) {
			return &command.ApplyCommand{
				Meta: meta,
			}, nil
		},

		"console": func() (cli.Command, error) {
			return &command.ConsoleCommand{
				Meta: meta,
			}, nil
		},

		"destroy": func() (cli.Command, error) {
			return &command.ApplyCommand{
				Meta:    meta,
				Destroy: true,
			}, nil
		},

		"env": func() (cli.Command, error) {
			return &command.WorkspaceCommand{
				Meta:       meta,
				LegacyName: true,
			}, nil
		},

		"env list": func() (cli.Command, error) {
			return &command.WorkspaceListCommand{
				Meta:       meta,
				LegacyName: true,
			}, nil
		},

		"env select": func() (cli.Command, error) {
			return &command.WorkspaceSelectCommand{
				Meta:       meta,
				LegacyName: true,
			}, nil
		},

		"env new": func() (cli.Command, error) {
			return &command.WorkspaceNewCommand{
				Meta:       meta,
				LegacyName: true,
			}, nil
		},

		"env delete": func() (cli.Command, error) {
			return &command.WorkspaceDeleteCommand{
				Meta:       meta,
				LegacyName: true,
			}, nil
		},

		"fmt": func() (cli.Command, error) {
			return &command.FmtCommand{
				Meta: meta,
			}, nil
		},

		"get": func() (cli.Command, error) {
			return &command.GetCommand{
				Meta: meta,
			}, nil
		},

		"graph": func() (cli.Command, error) {
			return &command.GraphCommand{
				Meta: meta,
			}, nil
		},

		"import": func() (cli.Command, error) {
			return &command.ImportCommand{
				Meta: meta,
			}, nil
		},

		"init": func() (cli.Command, error) {
			return &command.InitCommand{
				Meta: meta,
			}, nil
		},

		"login": func() (cli.Command, error) {
			return &command.LoginCommand{
				Meta: meta,
			}, nil
		},

		"logout": func() (cli.Command, error) {
			return &command.LogoutCommand{
				Meta: meta,
			}, nil
		},

		"output": func() (cli.Command, error) {
			return &command.OutputCommand{
				Meta: meta,
			}, nil
		},

		"plan": func() (cli.Command, error) {
			return &command.PlanCommand{
				Meta: meta,
			}, nil
		},

		"providers": func() (cli.Command, error) {
			return &command.ProvidersCommand{
				Meta: meta,
			}, nil
		},

		"providers lock": func() (cli.Command, error) {
			return &command.ProvidersLockCommand{
				Meta: meta,
			}, nil
		},

		"providers mirror": func() (cli.Command, error) {
			return &command.ProvidersMirrorCommand{
				Meta: meta,
			}, nil
		},

		"providers schema": func() (cli.Command, error) {
			return &command.ProvidersSchemaCommand{
				Meta: meta,
			}, nil
		},

		"push": func() (cli.Command, error) {
			return &command.PushCommand{
				Meta: meta,
			}, nil
		},

		"refresh": func() (cli.Command, error) {
			return &command.RefreshCommand{
				Meta: meta,
			}, nil
		},

		"show": func() (cli.Command, error) {
			return &command.ShowCommand{
				Meta: meta,
			}, nil
		},

		"taint": func() (cli.Command, error) {
			return &command.TaintCommand{
				Meta: meta,
			}, nil
		},

		"test": func() (cli.Command, error) {
			return &command.TestCommand{
				Meta: meta,
			}, nil
		},

		"validate": func() (cli.Command, error) {
			return &command.ValidateCommand{
				Meta: meta,
			}, nil
		},

		"version": func() (cli.Command, error) {
			return &command.VersionCommand{
				Meta:              meta,
				Version:           Version,
				VersionPrerelease: VersionPrerelease,
				Platform:          getproviders.CurrentPlatform,
				CheckFunc:         commandVersionCheck,
			}, nil
		},

		"untaint": func() (cli.Command, error) {
			return &command.UntaintCommand{
				Meta: meta,
			}, nil
		},

		"workspace": func() (cli.Command, error) {
			return &command.WorkspaceCommand{
				Meta: meta,
			}, nil
		},

		"workspace list": func() (cli.Command, error) {
			return &command.WorkspaceListCommand{
				Meta: meta,
			}, nil
		},

		"workspace select": func() (cli.Command, error) {
			return &command.WorkspaceSelectCommand{
				Meta: meta,
			}, nil
		},

		"workspace show": func() (cli.Command, error) {
			return &command.WorkspaceShowCommand{
				Meta: meta,
			}, nil
		},

		"workspace new": func() (cli.Command, error) {
			return &command.WorkspaceNewCommand{
				Meta: meta,
			}, nil
		},

		"workspace delete": func() (cli.Command, error) {
			return &command.WorkspaceDeleteCommand{
				Meta: meta,
			}, nil
		},

		//-----------------------------------------------------------
		// Plumbing
		//-----------------------------------------------------------

		"force-unlock": func() (cli.Command, error) {
			return &command.UnlockCommand{
				Meta: meta,
			}, nil
		},

		"state": func() (cli.Command, error) {
			return &command.StateCommand{}, nil
		},

		"state list": func() (cli.Command, error) {
			return &command.StateListCommand{
				Meta: meta,
			}, nil
		},

		"state rm": func() (cli.Command, error) {
			return &command.StateRmCommand{
				StateMeta: command.StateMeta{
					Meta: meta,
				},
			}, nil
		},

		"state mv": func() (cli.Command, error) {
			return &command.StateMvCommand{
				StateMeta: command.StateMeta{
					Meta: meta,
				},
			}, nil
		},

		"state pull": func() (cli.Command, error) {
			return &command.StatePullCommand{
				Meta: meta,
			}, nil
		},

		"state push": func() (cli.Command, error) {
			return &command.StatePushCommand{
				Meta: meta,
			}, nil
		},

		"state show": func() (cli.Command, error) {
			return &command.StateShowCommand{
				Meta: meta,
			}, nil
		},

		"state replace-provider": func() (cli.Command, error) {
			return &command.StateReplaceProviderCommand{
				StateMeta: command.StateMeta{
					Meta: meta,
				},
			}, nil
		},
	}

	PrimaryCommands = []string{
		"init",
		"validate",
		"plan",
		"apply",
		"destroy",
	}

	HiddenCommands = map[string]struct{}{
		"env":             struct{}{},
		"internal-plugin": struct{}{},
		"push":            struct{}{},
	}

	return commands
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
