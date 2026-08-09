#pragma once

#include <skydds/Export.h>

#include <string>

namespace skydds
{

struct Options
{
	std::string in;
	std::string out;
	std::string game = "se";
	unsigned int jobs = 0; // 0 = all cores
	BlockFormat format = BlockFormat::BC7;
	bool srgb = false;
	AlphaKind alphaKind = AlphaKind::None;
	float alphaRef = 0.5f; // alpha test threshold, used with AlphaKind::Test
	bool resizePow2 = false;
	bool dryRun = false;
	bool verbose = false;
};

bool parseCommandLine(Options& options, int& outExit, int argc, const char** argv);

} // namespace skydds
