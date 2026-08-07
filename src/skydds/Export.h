#pragma once

#include "Format.h"

#include <string>

namespace skydds
{

struct ExportRequest
{
	std::string inputPath;
	std::string outputPath;
	BlockFormat format = BlockFormat::BC7;
	bool srgb = false;
	AlphaKind alphaKind = AlphaKind::None;
	bool resizePow2 = false;
	bool dryRun = false;
	unsigned int threads = 0; // 0 = use all
};

struct ExportResult
{
	bool success = false;
	std::string error;        // set when !success
	bool usageError = false;  // bad arguments rather than a runtime failure

	unsigned int width = 0;
	unsigned int height = 0;
	unsigned int mipLevels = 0;
};

ExportResult exportTexture(const ExportRequest& request);

} // namespace skydds
