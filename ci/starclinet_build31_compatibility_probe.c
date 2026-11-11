// STARCLINET Build 31: harmless first-party dynamic-link verification probe.
// No hooks, interprocess access, game-file writes, or automatic initializers.
// The exported symbol permits future explicit app-only smoke tests.
#include <stdint.h>

__attribute__((visibility("default")))
uint32_t STARCLINETCompatibilityProbeVersion(void) {
    return 31u;
}
