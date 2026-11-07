# DigitalDoorKey build integration

Based on rednblkx/DigitalDoorKey at
`80e4a1e14eab3646b62ab3bdad6d2ed01d399375`, with Arduino ESP32 packaging
and an isolated private TLV type. The upstream ESP-IDF CMake/Kconfig and host
test projects remain available.

## Arduino ESP32 / PlatformIO

`library.json` supports Arduino and ESP-IDF on ESP32. The extra script configures
only standalone Arduino builds; ESP-IDF and hybrid Arduino-as-IDF-component
builds retain CMake/Kconfig control. Select one protocol in the consuming environment:

```ini
custom_ddk_protocol = homekey
; Optional, library-local ESP log threshold: 0 (off) through 5 (verbose).
custom_ddk_log_level = 0
```

`custom_ddk_protocol = aliro` is the default, matching the native IDF Kconfig
default. It includes Aliro NFC/BLE sources and excludes HomeKey-specific sources;
`homekey` does the reverse. Headers remain visible for both protocols, but callers
must only use APIs from their selected stack. The consuming project must provide
a C++20-or-newer toolchain and compatible ESP32 core crypto/CBOR libraries.

The script adds private include paths, the selected `CONFIG_DDK_PROTOCOL_*`
definition and source filters only to the library's build environment. It does
not define `CONFIG_IDF_CMAKE`. ESP logging, RNG and zeroization paths are selected
by the actual `ESP_PLATFORM` / `ARDUINO_ARCH_ESP32` platform definitions.
Logging follows the SDK/application policy unless `custom_ddk_log_level` is set.

TinyCBOR 0.6.0 headers from Intel TinyCBOR revision
`d393c16f3eb30d0c47e6f9d92db62272f0ec4dc7` are provided under
`compat/arduino/tinycbor`, with their MIT license. Arduino alone adds this
directory to its include search path, compensating for the SDK forwarding header
whose source submodule is absent from the Arduino distribution. These are headers,
not another compiled CBOR implementation; the linked core CBOR must be compatible.
All sources use `<cbor.h>`, including the Aliro sources.

## Native ESP-IDF and host tests

Native ESP-IDF continues to select the protocol through `Kconfig` and compile the
sources selected by `CMakeLists.txt`. `idf_component.yml` supplies its dependencies.
The Arduino script makes no changes to an ESP-IDF-only construction environment;
the Arduino compatibility headers are outside all IDF/host public include paths.

The standalone host tests use their own fetched TinyCBOR, mbedTLS and libsodium,
and build Aliro NFC/BLE flows without ESP32 platform definitions:

```sh
cmake -S tests -B /tmp/ddk-host-tests -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/ddk-host-tests --parallel
ctest --test-dir /tmp/ddk-host-tests --output-on-failure
python3 tests/platformio_packaging_test.py
```

## TLV coexistence

The private implementation is named `DdkTlv8`: HomeSpan defines an incompatible
global `TLV8` with overlapping method symbols. Distinct names prevent the linker
from binding DigitalDoorKey calls to HomeSpan's implementation. Both HomeKey and
Aliro use the isolated type; TLV8/BER wire formats are unchanged.
`tests/tlv8_coexistence_test.cpp` checks coexistence and round trips; it also runs
standalone with a C++20 compiler and `-I priv`.

Build coverage and outstanding hardware validation are recorded with each change;
neither packaging nor simulated protocol tests establish physical reader support.

## Validation of the packaging rework (2026-11-07)

* `debug_REG1_ESP_PN7161_IP` compiled and linked successfully with the explicitly
  selected HomeKey stack, Arduino-ESP32 3.3.8 / ESP-IDF 5.5.4.
* All six packaging regression tests passed, including comparison with the
  native IDF CMake source selections for both protocols. The IDF component
  registration is simulated in this test; it is not a full ESP-IDF SDK build.
* The standalone host suite compiled with its own TinyCBOR headers and libraries.
  Twelve of thirteen CTest executables passed. `aliro_ble_flow_test` failed two
  assertions (completed-status payload and time-sync callback count). The same
  two failures were reproduced from the prior committed revision `c74c30c` in a
  separate build, so they are pre-existing and outside this packaging change.

No new native ESP-IDF firmware build or hardware validation was performed.
