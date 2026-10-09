# Local OpenKNX Arduino wrapper

Branch: `v1dev_HomeKey`. Upstream: https://github.com/rednblkx/DigitalDoorKey
at `80e4a1e14eab3646b62ab3bdad6d2ed01d399375`. This includes the upstream
move of `ddk_crypto_shims.h` into the public include directory; the Arduino
wrapper and its private-header search path remain intact.

The PlatformIO wrapper selects Home Key sources, ESP-IDF crypto/RNG/logging
paths, and private include files. Aliro and BLE sources are excluded. Crypto
uses the Arduino core's mbedTLS and libsodium; no crypto implementation changes.
Upstream credential logging is compiled out with `LOG_LOCAL_LEVEL=0`.

TinyCBOR 0.6.0 headers from Intel's repository (commit
`d393c16f3eb30d0c47e6f9d92db62272f0ec4dc7`) are under `include/tinycbor`,
with their MIT license. They match the CBOR library bundled in ESP-IDF 5.4.
The four CBOR includes explicitly select these headers rather than an SDK
forwarding header whose source submodule is absent in the Arduino distribution.

Validated with Arduino-ESP32 3.2.1 / ESP-IDF 5.4 / Xtensa GCC 14.2 in the
OpenKNX XIAO ESP32-S3 Home Key environment. This wrapper is Arduino ESP32 only;
it does not change the upstream IDF component build. No remote publication.
