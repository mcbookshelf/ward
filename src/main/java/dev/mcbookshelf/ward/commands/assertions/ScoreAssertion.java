package dev.mcbookshelf.ward.commands.assertions;

import java.util.function.BiPredicate;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.advancements.predicates.MinMaxBounds;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.ObjectiveArgument;
import net.minecraft.commands.arguments.RangeArgument;
import net.minecraft.commands.arguments.ScoreHolderArgument;
import net.minecraft.network.chat.Component;
import net.minecraft.world.scores.Objective;
import net.minecraft.world.scores.ReadOnlyScoreInfo;
import net.minecraft.world.scores.ScoreHolder;
import net.minecraft.world.scores.Scoreboard;

import dev.mcbookshelf.ward.TestExecutor;

/**
 * Asserts scoreboard comparisons: score against score, or score against a range.
 */
class ScoreAssertion implements Assertion {
	@Override
	public void attach(LiteralArgumentBuilder<CommandSourceStack> root, Context context) {
		root.then(Commands.literal("score")
				.then(Commands.argument("target", ScoreHolderArgument.scoreHolder())
						.suggests(ScoreHolderArgument.SUGGEST_SCORE_HOLDERS)
						.then(Commands.argument("target_objective", ObjectiveArgument.objective())
								.then(buildScore(context, Integer::equals, "="))
								.then(buildScore(context, (a, b) -> a < b, "<"))
								.then(buildScore(context, (a, b) -> a <= b, "<="))
								.then(buildScore(context, (a, b) -> a > b, ">"))
								.then(buildScore(context, (a, b) -> a >= b, ">="))
								.then(Commands.literal("matches")
										.then(Commands.argument("range", RangeArgument.intRange())
												.executes(ctx -> assertScoreRange(ctx, context)))))));
	}

	/**
	 * Builds a score comparison subcommand for a specific operator.
	 */
	private static LiteralArgumentBuilder<CommandSourceStack> buildScore(
			Context context,
			BiPredicate<Integer, Integer> predicate,
			String op) {
		return Commands.literal(op)
				.then(Commands.argument("source", ScoreHolderArgument.scoreHolder())
						.suggests(ScoreHolderArgument.SUGGEST_SCORE_HOLDERS)
						.then(Commands.argument("source_objective", ObjectiveArgument.objective())
								.executes(ctx -> assertScore(ctx, context, predicate, op))));
	}

	/**
	 * Asserts that a scoreboard comparison between two scores holds true.
	 *
	 * @param op the operator symbol (=, <, <=, >, >=) used for error messages
	 */
	private static int assertScore(
			CommandContext<CommandSourceStack> context,
			Context assertion,
			BiPredicate<Integer, Integer> operation,
			String op) throws CommandSyntaxException {
		Scoreboard scoreboard = context.getSource().getServer().getScoreboard();

		return assertion.apply(() -> {
			ScoreHolder target = ScoreHolderArgument.getName(context, "target");
			ScoreHolder source = ScoreHolderArgument.getName(context, "source");
			Objective targetObjective = ObjectiveArgument.getObjective(context, "target_objective");
			Objective sourceObjective = ObjectiveArgument.getObjective(context, "source_objective");
			ReadOnlyScoreInfo targetScore = scoreboard.getPlayerScoreInfo(target, targetObjective);
			ReadOnlyScoreInfo sourceScore = scoreboard.getPlayerScoreInfo(source, sourceObjective);
			int count = (targetScore != null && sourceScore != null && operation.test(targetScore.value(), sourceScore.value())) ? 1 : 0;

			return new TestExecutor.AssertResult(count, negated -> Component.translatable(
					Assertions.getTranslationKey("score", negated),
					target.getScoreboardName(),
					targetObjective.getName(),
					op,
					source.getScoreboardName(),
					sourceObjective.getName(),
					targetScore != null ? targetScore.value() : "undefined",
					op,
					sourceScore != null ? sourceScore.value() : "undefined"));
		});
	}

	/**
	 * Asserts that a score value matches the specified range.
	 */
	private static int assertScoreRange(CommandContext<CommandSourceStack> context, Context assertion) throws CommandSyntaxException {
		MinMaxBounds.Ints range = RangeArgument.Ints.getRange(context, "range");
		Scoreboard scoreboard = context.getSource().getServer().getScoreboard();

		return assertion.apply(() -> {
			ScoreHolder target = ScoreHolderArgument.getName(context, "target");
			Objective targetObjective = ObjectiveArgument.getObjective(context, "target_objective");
			ReadOnlyScoreInfo scoreInfo = scoreboard.getPlayerScoreInfo(target, targetObjective);
			int count = (scoreInfo != null && range.matches(scoreInfo.value())) ? 1 : 0;

			return new TestExecutor.AssertResult(count, negated -> Component.translatable(
					Assertions.getTranslationKey("score_range", negated),
					target.getScoreboardName(),
					targetObjective.getName(),
					Assertions.getRawArgument(context, "range"),
					scoreInfo != null ? scoreInfo.value() : "undefined"));
		});
	}
}
