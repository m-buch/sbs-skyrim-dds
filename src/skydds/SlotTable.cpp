#include "SlotTable.h"

#include <cstring>
#include <string>

namespace skydds
{

namespace
{

const BlockFormat noVariant = BlockFormat::BC1;

const Slot slots[] =
{
	{"diffuse", BlockFormat::BC1, BlockFormat::BC7, BlockFormat::BC1a, true, true,
		AlphaKind::Standard, true},
	{"normal", BlockFormat::BC7, noVariant, noVariant, false, false, AlphaKind::Encoded, true},
	{"glow", BlockFormat::BC1, noVariant, noVariant, false, true, AlphaKind::None, true},
	{"parallax", BlockFormat::BC4, noVariant, noVariant, false, false, AlphaKind::None, true},
	{"environment", BlockFormat::BC1, noVariant, noVariant, false, true, AlphaKind::None, false},
	{"envmask", BlockFormat::BC4, noVariant, noVariant, false, false, AlphaKind::None, true},
	{"multilayer", BlockFormat::BC7, noVariant, noVariant, false, true, AlphaKind::Standard,
		true},
	{"backlight", BlockFormat::BC1, noVariant, noVariant, false, false, AlphaKind::None, true},
	{"msn", BlockFormat::BC7, noVariant, noVariant, false, false, AlphaKind::None, true},
};

} // namespace

const Slot* findSlot(const char* name)
{
	for (const Slot& slot : slots)
	{
		if (std::strcmp(slot.name, name) == 0)
			return &slot;
	}
	return nullptr;
}

const char* slotNames()
{
	static const std::string names = []
	{
		std::string result;
		for (const Slot& slot : slots)
		{
			if (!result.empty())
				result += ' ';
			result += slot.name;
		}
		return result;
	}();
	return names.c_str();
}

} // namespace skydds
