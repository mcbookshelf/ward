package dev.mcbookshelf.ward.mixin;

import com.mojang.brigadier.context.ContextChain;
import org.jspecify.annotations.Nullable;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;

import dev.mcbookshelf.ward.coverage.CoverageLineHolder;
import dev.mcbookshelf.ward.coverage.FunctionCoverage;

/**
 * Stamped once when its function is built, read on every dispatch.
 */
@Mixin(value = ContextChain.class, remap = false)
public class ContextChainMixin implements CoverageLineHolder {
	@Unique
	private FunctionCoverage.@Nullable Line ward$coverageLine;

	@Override
	public FunctionCoverage.@Nullable Line ward$coverageLine() {
		return this.ward$coverageLine;
	}

	@Override
	public void ward$coverageLine(FunctionCoverage.Line line) {
		this.ward$coverageLine = line;
	}
}
