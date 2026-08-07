#include "Cli.h"

#include <skydds/SlotTable.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace skydds
{

namespace
{

const char* usage =
	"Usage: skydds --in <file.png> --out <file.dds> --slot <slot> [options]\n"
	"\n"
	"Convert a source image to a Skyrim SE DDS (BC-compressed, full mip chain).\n"
	"\n"
	"Required:\n"
	"  --in <file>       Source image (PNG or anything FreeImage loads).\n"
	"  --out <file>      Output DDS path.\n"
	"  --slot <slot>     Semantic slot; format selection is internal.\n"
	"                    Slots: %s\n"
	"\n"
	"Options:\n"
	"  --game se         Target game (only 'se' is supported).\n"
	"  --jobs <N>        Encoder threads (default: all cores).\n"
	"  --resize pow2     Round non-power-of-two dimensions up to the next power of two.\n"
	"  --alpha-mode <m>  Diffuse only: auto (default), none, blend, or test.\n"
	"                    auto detects from image content; none forces the opaque\n"
	"                    format; blend selects the RGBA format; test means the\n"
	"                    material alpha-tests (never blends), 1-bit alpha format.\n"
	"  --alpha-ref <x>   Accepted and ignored (reserved for alpha coverage preservation).\n"
	"  --dry-run         Print the resolved format/settings without writing.\n"
	"  --verbose         Print progress detail.\n"
	"  --help            Show this help.\n";

bool fail(int& outExit, const char* message, const char* detail = nullptr)
{
	if (detail)
		std::fprintf(stderr, "skydds: %s '%s'\n", message, detail);
	else
		std::fprintf(stderr, "skydds: %s\n", message);
	std::fprintf(stderr, "Run 'skydds --help' for usage.\n");
	outExit = 2;
	return false;
}

} // namespace

bool parseCommandLine(Options& options, int& outExit, int argc, const char** argv)
{
	auto value = [&](int& i) -> const char*
	{
		if (i + 1 >= argc)
			return nullptr;
		return argv[++i];
	};

	for (int i = 1; i < argc; ++i)
	{
		const char* arg = argv[i];
		if (std::strcmp(arg, "--help") == 0 || std::strcmp(arg, "-h") == 0)
		{
			std::printf(usage, slotNames());
			outExit = 0;
			return false;
		}
		else if (std::strcmp(arg, "--in") == 0)
		{
			const char* v = value(i);
			if (!v)
				return fail(outExit, "--in requires a value");
			options.in = v;
		}
		else if (std::strcmp(arg, "--out") == 0)
		{
			const char* v = value(i);
			if (!v)
				return fail(outExit, "--out requires a value");
			options.out = v;
		}
		else if (std::strcmp(arg, "--slot") == 0)
		{
			const char* v = value(i);
			if (!v)
				return fail(outExit, "--slot requires a value");
			options.slot = v;
		}
		else if (std::strcmp(arg, "--game") == 0)
		{
			const char* v = value(i);
			if (!v)
				return fail(outExit, "--game requires a value");
			options.game = v;
		}
		else if (std::strcmp(arg, "--jobs") == 0)
		{
			const char* v = value(i);
			char* end = nullptr;
			long jobs = v ? std::strtol(v, &end, 10) : 0;
			if (!v || *end != '\0' || jobs < 1)
				return fail(outExit, "--jobs requires a positive integer");
			options.jobs = static_cast<unsigned int>(jobs);
		}
		else if (std::strcmp(arg, "--resize") == 0)
		{
			const char* v = value(i);
			if (!v || std::strcmp(v, "pow2") != 0)
				return fail(outExit, "--resize only supports 'pow2'");
			options.resizePow2 = true;
		}
		else if (std::strcmp(arg, "--alpha-mode") == 0)
		{
			const char* v = value(i);
			if (!v)
				return fail(outExit, "--alpha-mode requires a value");
			if (std::strcmp(v, "auto") == 0)
				options.alphaMode = AlphaMode::Auto;
			else if (std::strcmp(v, "none") == 0)
				options.alphaMode = AlphaMode::None;
			else if (std::strcmp(v, "blend") == 0)
				options.alphaMode = AlphaMode::Blend;
			else if (std::strcmp(v, "test") == 0)
				options.alphaMode = AlphaMode::Test;
			else
				return fail(outExit, "--alpha-mode must be auto, none, blend, or test; got", v);
		}
		else if (std::strcmp(arg, "--alpha-ref") == 0)
		{
			// for alpha coverage preservation later
			if (!value(i))
				return fail(outExit, "--alpha-ref requires a value");
		}
		else if (std::strcmp(arg, "--dry-run") == 0)
			options.dryRun = true;
		else if (std::strcmp(arg, "--verbose") == 0)
			options.verbose = true;
		else
			return fail(outExit, "unknown argument", arg);
	}

	if (options.in.empty())
		return fail(outExit, "--in is required");
	if (options.out.empty())
		return fail(outExit, "--out is required");
	if (options.slot.empty())
		return fail(outExit, "--slot is required");
	if (options.game != "se")
		return fail(outExit, "only '--game se' is supported; got", options.game.c_str());
	return true;
}

} // namespace skydds
