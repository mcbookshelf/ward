package dev.mcbookshelf.ward.daemon;

import com.mojang.brigadier.exceptions.CommandSyntaxException;

interface Runner {
	boolean tick() throws CommandSyntaxException;

	sealed interface Options permits TestRunner.Options, BenchRunner.Options {
	}
}
