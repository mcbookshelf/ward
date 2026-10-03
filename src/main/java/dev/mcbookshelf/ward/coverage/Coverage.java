package dev.mcbookshelf.ward.coverage;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import net.minecraft.SharedConstants;
import net.minecraft.server.packs.PackType;
import net.minecraft.server.packs.metadata.pack.PackFormat;

public final class Coverage {
	private static volatile boolean enabled;

	private Coverage() {
	}

	public static boolean isEnabled() {
		return enabled;
	}

	public static void reset(boolean enable) {
		enabled = false;
		FunctionCoverage.clear();
		DataCoverage.clear();
		enabled = enable;
	}

	public static JsonObject report() {
		JsonObject report = new JsonObject();
		report.add("functions", FunctionCoverage.report());
		report.add("conditions", DataCoverage.conditions());
		report.add("runs", DataCoverage.runs());
		// The client needs it to know which overlays of a pack were loaded
		report.add("pack_format", packFormat());
		return report;
	}

	private static JsonArray packFormat() {
		PackFormat format = SharedConstants.getCurrentVersion().packVersion(PackType.SERVER_DATA);
		JsonArray array = new JsonArray();
		array.add(format.major());
		array.add(format.minor());
		return array;
	}
}
