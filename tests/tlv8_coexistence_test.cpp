#include "TLV8.hpp"
#include <cassert>

// Model the foreign global API that previously collided at link time.
class TLV8 {
public:
    void add(uint8_t, size_t, const uint8_t*) {}
};

int main() {
    TLV8 foreign;
    foreign.add(2, 0, nullptr);

    DdkTlv8 status;
    status.add(2, static_cast<uint8_t>(0));
    assert((status.get() == std::vector<uint8_t>{2, 1, 0}));

    DdkTlv8 response;
    response.add(7, status.get());
    const auto encoded = response.get();
    assert((encoded == std::vector<uint8_t>{7, 3, 2, 1, 0}));

    DdkTlv8 parsed;
    parsed.parse(encoded.data(), encoded.size());
    assert(parsed.ok());
    std::vector<uint8_t> value;
    assert(parsed.get(7, value) && value == status.get());

    const std::vector<uint8_t> large(300, 0xA5);
    for (bool ber : {false, true}) {
        DdkTlv8 original(ber);
        original.add(1, large);
        const auto packed = original.get();
        DdkTlv8 decoded(ber);
        decoded.parse(packed.data(), packed.size());
        assert(decoded.ok());
        assert(decoded.get(1, value) && value == large);
    }
}
