package dev.mcbookshelf.ward.commands.assertions;

import java.util.List;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;

import net.minecraft.commands.CommandSourceStack;

public final class Assertions {
	private static final List<Assertion> CONDITIONS = List.of(
			new BiomeAssertion(),
			new BlockAssertion(),
			new BlocksAssertion(),
			new ChatAssertion(),
			new DataAssertion(),
			new DimensionAssertion(),
			new EntityAssertion(),
			new FunctionAssertion(),
			new ItemsAssertion(),
			new LoadedAssertion(),
			new PredicateAssertion(),
			new RunAssertion(),
			new ScoreAssertion(),
			new SlotsAssertion(),
			new StopwatchAssertion());

	private Assertions() {
	}

	/**
	 * Attaches every condition to the given assert/await literal.
	 */
	public static LiteralArgumentBuilder<CommandSourceStack> build(
			LiteralArgumentBuilder<CommandSourceStack> root,
			Assertion.Context assertion) {
		for (Assertion condition : CONDITIONS) {
			condition.attach(root, assertion);
		}

		return root;
	}
}
