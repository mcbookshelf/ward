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
import net.minecraft.world.scores.Objective;
import net.minecraft.world.scores.ReadOnlyScoreInfo;
import net.minecraft.world.scores.ScoreHolder;
import net.minecraft.world.scores.Scoreboard;

import dev.mcbookshelf.ward.AssertResult;

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
												.executes(ctx -> runRange(ctx, context)))))));
	}

	private static LiteralArgumentBuilder<CommandSourceStack> buildScore(
			Context context,
			BiPredicate<Integer, Integer> predicate,
			String op) {
		return Commands.literal(op)
				.then(Commands.argument("source", ScoreHolderArgument.scoreHolder())
						.suggests(ScoreHolderArgument.SUGGEST_SCORE_HOLDERS)
						.then(Commands.argument("source_objective", ObjectiveArgument.objective())
								.executes(ctx -> run(ctx, context, predicate, op))));
	}

	private static int run(
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

			return AssertResult.of(count, "score",
					target.getScoreboardName(),
					targetObjective.getName(),
					op,
					source.getScoreboardName(),
					sourceObjective.getName(),
					targetScore != null ? targetScore.value() : "undefined",
					op,
					sourceScore != null ? sourceScore.value() : "undefined");
		});
	}

	private static int runRange(CommandContext<CommandSourceStack> context, Context assertion) throws CommandSyntaxException {
		MinMaxBounds.Ints range = RangeArgument.Ints.getRange(context, "range");
		Scoreboard scoreboard = context.getSource().getServer().getScoreboard();

		return assertion.apply(() -> {
			ScoreHolder target = ScoreHolderArgument.getName(context, "target");
			Objective targetObjective = ObjectiveArgument.getObjective(context, "target_objective");
			ReadOnlyScoreInfo scoreInfo = scoreboard.getPlayerScoreInfo(target, targetObjective);
			int count = (scoreInfo != null && range.matches(scoreInfo.value())) ? 1 : 0;

			return AssertResult.of(count, "score_range",
					target.getScoreboardName(),
					targetObjective.getName(),
					Assertion.getRawArgument(context, "range"),
					scoreInfo != null ? scoreInfo.value() : "undefined");
		});
	}
}
