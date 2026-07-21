package dev.mcbookshelf.ward.commands.assertions;

import java.util.List;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;

import net.minecraft.commands.CommandSourceStack;

public final class Assertions {
	private static final List<Assertion> CONDITIONS = List.of(
			new BiomeAssertion(),
			new BlockAssertion(),
			new ChatAssertion(),
			new DataAssertion(),
			new EntityAssertion(),
			new FunctionAssertion(),
			new ItemsAssertion(),
			new PredicateAssertion(),
			new RunAssertion(),
			new ScoreAssertion());

	private Assertions() {
	}

	/**
	 * Attaches every condition to the given assert/await literal.
	 */
	public static LiteralArgumentBuilder<CommandSourceStack> build(
			LiteralArgumentBuilder<CommandSourceStack> root,
			Assertion.Context context) {
		for (Assertion condition : CONDITIONS) {
			condition.attach(root, context);
		}

		return root;
	}
}
