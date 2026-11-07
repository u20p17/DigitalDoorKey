"""Arduino-only packaging; native ESP-IDF uses CMake/Kconfig unchanged."""
from pathlib import Path
from SCons.Script import Dir


def configure(env, root):
    frameworks = env.get("PIOFRAMEWORK", [])
    # Hybrid Arduino-as-IDF-component builds also belong to CMake/Kconfig.
    if "arduino" not in frameworks or "espidf" in frameworks:
        return

    protocol = env.GetProjectOption("custom_ddk_protocol", "aliro").strip().lower()
    filters = {
        "homekey": ["+<*>", "-<aliro/>", "-<auth/Aliro*>",
                    "-<crypto/GcmSecureChannel.cpp>", "-<utils/BerTlv.cpp>",
                    "-<transport/Ble*>"],
        "aliro": ["+<*>", "-<homekey/>", "-<auth/HK*>", "-<auth/Attestation*>",
                  "-<crypto/ScbSecureChannel.cpp>", "-<crypto/ISO18013SecureContext.cpp>",
                  "-<utils/ndef.cpp>", "-<utils/HK_HomeKit.cpp>"],
    }
    if protocol not in filters:
        raise ValueError("custom_ddk_protocol must be aliro or homekey")

    definitions = [("CONFIG_DDK_PROTOCOL_" + protocol.upper(), 1)]
    # Leave SDK/application logging policy alone unless explicitly overridden.
    log_level = env.GetProjectOption("custom_ddk_log_level", "").strip()
    if log_level:
        if log_level not in {"0", "1", "2", "3", "4", "5"}:
            raise ValueError("custom_ddk_log_level must be an integer from 0 to 5")
        definitions.append(("LOG_LOCAL_LEVEL", int(log_level)))

    # These paths/defines belong only to this library's construction environment.
    env.Append(CPPPATH=[str(root / "priv"), str(root / "compat/arduino/tinycbor")],
               CPPDEFINES=definitions)
    env.Replace(SRC_FILTER=filters[protocol])


Import("env")
configure(env, Path(Dir(".").srcnode().abspath))
