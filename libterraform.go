package main

import "C"
import (
	"github.com/hashicorp/terraform/internal/configs"
	"github.com/hashicorp/terraform/internal/experiments"
	"unsafe"
)

/*
   #include <stdlib.h>
*/
import "C"

import (
	"encoding/json"
)

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

//export LoadConfigDir
func LoadConfigDir(cPath *C.char) (cMod *C.char, cDiags *C.char, cError *C.char) {
	defer func() {
		recover()
	}()

	parser := configs.NewParser(nil)
	path := C.GoString(cPath)
	//fmt.Println(path)
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
	//fmt.Println(string(modBytes), string(diagsBytes))
	return cMod, cDiags, cError
}

//export Free
func Free(cString *int) {
	C.free(unsafe.Pointer(cString))
}

func main() {}
