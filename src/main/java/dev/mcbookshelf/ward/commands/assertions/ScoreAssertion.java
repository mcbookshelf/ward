package dev.mcbookshelf.ward.commands.assertions;

import java.util.function.BiPredicate;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;

import net.minecraft.advancements.predicates.MinMaxBounds;
import net.minecraft.commands.CommandBuildContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.ObjectiveArgument;
import net.minecraft.commands.arguments.RangeArgument;
import net.minecraft.commands.arguments.ScoreHolderArgument;
import net.minecraft.world.scores.Objective;
import net.minecraft.world.scores.ReadOnlyScoreInfo;
import net.minecraft.world.scores.ScoreHolder;
import net.minecraft.world.scores.Scoreboard;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.test.AssertResult;

class ScoreAssertion implements Assertion {
	@Override
	public void attach(
			LiteralArgumentBuilder<CommandSourceStack> root,
			CommandDispatcher<CommandSourceStack> dispatcher,
			CommandBuildContext context,
			Mode mode) {
		root.then(Commands.literal("score")
				.then(Commands.argument("target", ScoreHolderArgument.scoreHolder())
						.suggests(ScoreHolderArgument.SUGGEST_SCORE_HOLDERS)
						.then(Commands.argument("target_objective", ObjectiveArgument.objective())
								.then(buildScore(mode, Integer::equals, "="))
								.then(buildScore(mode, (a, b) -> a < b, "<"))
								.then(buildScore(mode, (a, b) -> a <= b, "<="))
								.then(buildScore(mode, (a, b) -> a > b, ">"))
								.then(buildScore(mode, (a, b) -> a >= b, ">="))
								.then(Commands.literal("matches")
										.then(Commands.argument("range", RangeArgument.intRange())
												.executes(ctx -> mode.check(ctx, ScoreAssertion::checkRange)))))));
	}

	private static LiteralArgumentBuilder<CommandSourceStack> buildScore(
			Mode mode,
			BiPredicate<Integer, Integer> predicate,
			String op) {
		return Commands.literal(op)
				.then(Commands.argument("source", ScoreHolderArgument.scoreHolder())
						.suggests(ScoreHolderArgument.SUGGEST_SCORE_HOLDERS)
						.then(Commands.argument("source_objective", ObjectiveArgument.objective())
								.executes(ctx -> mode.check(ctx, attempt -> check(attempt, predicate, op)))));
	}

	private static AssertResult check(CommandContext<CommandSourceStack> context, BiPredicate<Integer, Integer> operation, String op) throws CommandSyntaxException {
		Scoreboard scoreboard = context.getSource().getServer().getScoreboard();
		ScoreHolder target = ScoreHolderArgument.getName(context, "target");
		ScoreHolder source = ScoreHolderArgument.getName(context, "source");
		Objective targetObjective = ObjectiveArgument.getObjective(context, "target_objective");
		Objective sourceObjective = ObjectiveArgument.getObjective(context, "source_objective");
		ReadOnlyScoreInfo targetScore = scoreboard.getPlayerScoreInfo(target, targetObjective);
		ReadOnlyScoreInfo sourceScore = scoreboard.getPlayerScoreInfo(source, sourceObjective);
		boolean holds = targetScore != null && sourceScore != null && operation.test(targetScore.value(), sourceScore.value());

		return AssertResult.of(holds, negated -> Messages.translatable(
				negated ? "ward.assert.not_score" : "ward.assert.score",
				target.getScoreboardName(),
				targetObjective.getName(),
				op,
				source.getScoreboardName(),
				sourceObjective.getName(),
				targetScore != null ? targetScore.value() : "undefined",
				op,
				sourceScore != null ? sourceScore.value() : "undefined"));
	}

	private static AssertResult checkRange(CommandContext<CommandSourceStack> context) throws CommandSyntaxException {
		MinMaxBounds.Ints range = RangeArgument.Ints.getRange(context, "range");
		Scoreboard scoreboard = context.getSource().getServer().getScoreboard();
		ScoreHolder target = ScoreHolderArgument.getName(context, "target");
		Objective targetObjective = ObjectiveArgument.getObjective(context, "target_objective");
		ReadOnlyScoreInfo scoreInfo = scoreboard.getPlayerScoreInfo(target, targetObjective);

		return AssertResult.of(scoreInfo != null && range.matches(scoreInfo.value()), negated -> Messages.translatable(
				negated ? "ward.assert.not_score_range" : "ward.assert.score_range",
				target.getScoreboardName(),
				targetObjective.getName(),
				Assertion.getRawArgument(context, "range"),
				scoreInfo != null ? scoreInfo.value() : "undefined"));
	}
}
