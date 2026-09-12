package dev.mcbookshelf.ward.mixin;

import com.mojang.brigadier.context.ContextChain;
import org.jspecify.annotations.Nullable;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;

import dev.mcbookshelf.ward.CoverageRecorder;
import dev.mcbookshelf.ward.accessor.CoverageLineHolder;

/**
 * Stamped once when the owning function is instrumented, read on every dispatch.
 */
@Mixin(value = ContextChain.class, remap = false)
public class ContextChainMixin implements CoverageLineHolder {
	@Unique
	private CoverageRecorder.@Nullable Line ward$coverageLine;

	@Override
	public CoverageRecorder.@Nullable Line ward$coverageLine() {
		return this.ward$coverageLine;
	}

	@Override
	public void ward$coverageLine(CoverageRecorder.Line line) {
		this.ward$coverageLine = line;
	}
}
