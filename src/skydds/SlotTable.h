#pragma once

#include "Format.h"

namespace skydds
{

enum class AlphaKind
{
	None,     // no alpha
	Standard, // transparency
	Encoded   // data packed (f.e. specularity)
};

struct Slot
{
	const char* name;
	// Format when input has no alpha
	BlockFormat format;
	// Format when blended alpha is present
	BlockFormat formatAlpha;
	// Format when 1-bit alpha is present
	BlockFormat formatAlphaTest;
	bool hasAlphaVariants;
	bool srgb;
	AlphaKind alphaKind;
	// False: recognized but not implemented yet (env map)
	bool supported;
};

// Returns null if the slot name is unknown
const Slot* findSlot(const char* name);

// Space separated slot names
const char* slotNames();

} // namespace skydds
