package dev.mcbookshelf.ward.test;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.UUID;
import java.util.function.BooleanSupplier;
import java.util.function.Supplier;
import java.util.stream.Stream;

import com.mojang.brigadier.exceptions.CommandSyntaxException;
import org.jspecify.annotations.Nullable;

import net.minecraft.commands.CommandResultCallback;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.coordinates.Coordinates;
import net.minecraft.commands.execution.CommandQueueEntry;
import net.minecraft.commands.execution.EntryAction;
import net.minecraft.commands.execution.ExecutionContext;
import net.minecraft.commands.execution.Frame;
import net.minecraft.gametest.framework.GameTestException;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.gametest.framework.GameTestInfo;
import net.minecraft.gametest.framework.GameTestListener;
import net.minecraft.gametest.framework.GameTestRunner;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.gamerules.GameRules;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import dev.mcbookshelf.ward.Messages;
import dev.mcbookshelf.ward.Ward;
import dev.mcbookshelf.ward.dummy.Dummy;

public class TestExecutor {
	static @Nullable TestExecutor current;

	private @Nullable ExecutionContext<CommandSourceStack> context;
	private final List<BooleanSupplier> awaits = new ArrayList<>();
	private final List<Dummy> dummies = new ArrayList<>();
	private final GameTestHelper helper;
	private final GameTestInfo info;
	private final long chatSequence = ChatRecorder.sequence();
	private final int timeout;
	private int next;
	private int line;

	public TestExecutor(GameTestHelper helper) {
		this.helper = helper;
		this.info = helper.testInfo;
		this.info.addListener(new Cleanup());
		this.timeout = this.info.getTimeoutTicks();
	}

	public static TestExecutor current() throws CommandSyntaxException {
		if (current == null) throw Messages.error("ward.not_in_test");
		return current;
	}

	public static void trackDummy(Dummy dummy) {
		if (current != null) {
			current.dummies.add(dummy);
		}
	}

	public void run(TestFunction function) {
		CommandSourceStack source;
		current = this;

		try {
			source = createCommandSourceStack(function);
		} finally {
			current = null;
		}

		Runnable tick = () -> tick(function.commands(), source);
		this.helper.onEachTick(tick);
		this.helper.runAtTickTime(this.timeout, tick);
	}

	private void tick(List<TestFunction.Entry> commands, CommandSourceStack source) {
		current = this;

		try {
			for (BooleanSupplier await : List.copyOf(this.awaits)) {
				if (await.getAsBoolean()) this.awaits.remove(await);
			}

			while (this.next < commands.size() && !this.info.isDone() && this.awaits.isEmpty()) {
				execute(commands.get(this.next++), follow(source));
			}

			if (!this.info.isDone() && this.awaits.isEmpty()) {
				succeed();
			}
		} catch (GameTestException e) {
			fail(e);
		} catch (RuntimeException e) {
			Ward.LOGGER.error("Test {} crashed on line {}", this.info.id(), this.line, e);
			fail(failure(Component.literal(Messages.describe(e))));
		} finally {
			current = null;
		}
	}

	private void execute(TestFunction.Entry entry, CommandSourceStack sender) {
		this.line = entry.line();
		Commands.executeCommandInContext(sender, context -> {
			this.context = context;
			ExecutionContext.queueInitialCommandExecution(context, entry.command(), entry.chain(), sender, CommandResultCallback.EMPTY);
		});

		ExecutionContext<CommandSourceStack> used = Objects.requireNonNull(this.context);

		if (used.queueOverflow || used.commandQuota <= 0 && !used.commandQueue.isEmpty()) {
			int limit = this.helper.getLevel().getGameRules().get(GameRules.MAX_COMMAND_SEQUENCE_LENGTH);
			throw failure(Messages.translatable("ward.limit", limit));
		}
	}

	public void succeed() {
		this.helper.succeed();
	}

	private void fail(GameTestException e) {
		if (this.info.isDone()) return;
		this.info.fail(e);
		this.info.finish();
	}

	public void await(int delay) {
		long end = this.helper.getTick() + delay;
		if (end > this.timeout) throw failure(Messages.translatable("ward.timeout", this.timeout));
		this.awaits.add(() -> this.helper.getTick() >= end);
	}

	public int assertThat(AssertResult result, boolean negated) {
		if (satisfied(result, negated)) return negated ? 1 : result.count();
		throw failure(result.message().apply(negated));
	}

	public void awaitThat(AssertResult first, Supplier<AssertResult> poll, boolean negated) {
		if (satisfied(first, negated)) return;

		this.awaits.add(() -> {
			AssertResult result = poll.get();
			if (satisfied(result, negated)) return true;
			if (this.helper.getTick() < this.timeout) return false;
			throw failure(Messages.translatable("ward.await.timeout", result.message().apply(negated)));
		});
	}

	private static boolean satisfied(AssertResult result, boolean negated) {
		return negated ? result.count() == 0 && !result.errored() : result.count() > 0;
	}

	public AABB getBounds() {
		return this.helper.getBounds();
	}

	public Stream<String> chatMessages() {
		return ChatRecorder.since(this.chatSequence, this);
	}

	public Stream<String> chatMessages(UUID recipient) {
		return ChatRecorder.since(this.chatSequence, this, recipient);
	}

	public TestException failure(Component message) {
		return new TestException(message, this.line, this.helper.getTick());
	}

	public CommandSourceStack follow(CommandSourceStack source) {
		if (source.getEntity() instanceof Dummy dummy
				&& server().getPlayerList().getPlayer(dummy.getUUID()) instanceof Dummy live
				&& live != dummy) {
			return source.withEntity(live);
		}

		return source;
	}

	public void rerun(CommandSourceStack source, EntryAction<CommandSourceStack> action) {
		Commands.executeCommandInContext(source, context -> context.queueNext(
				new CommandQueueEntry<>(new Frame(0, CommandResultCallback.EMPTY, context.frameControlForDepth(0)), action)));
	}

	private CommandSourceStack createCommandSourceStack(TestFunction function) {
		CommandSourceStack source = server()
				.createCommandSourceStack()
				.withLevel(this.helper.getLevel())
				.withPosition(this.helper.absoluteVec(Vec3.ZERO))
				.withSuppressedOutput();

		Coordinates coordinates = function.directives().dummy();

		if (coordinates == null) {
			return source;
		}

		Dummy dummy = Dummy.create(this.helper.getLevel(), coordinates.getPosition(source), source.getRotation());
		this.dummies.add(dummy);
		return source.withEntity(dummy);
	}

	private MinecraftServer server() {
		return this.helper.getLevel().getServer();
	}

	private final class Cleanup implements GameTestListener {
		@Override
		public void testStructureLoaded(GameTestInfo testInfo) {
		}

		@Override
		public void testPassed(GameTestInfo testInfo, GameTestRunner runner) {
			end();
		}

		@Override
		public void testFailed(GameTestInfo testInfo, GameTestRunner runner) {
			end();
		}

		@Override
		public void testAddedForRerun(GameTestInfo original, GameTestInfo copy, GameTestRunner runner) {
		}

		private void end() {
			for (Dummy dummy : TestExecutor.this.dummies) {
				if (server().getPlayerList().getPlayer(dummy.getUUID()) instanceof Dummy connected) {
					connected.leave(Component.literal("Test finished"));
				}
			}
		}
	}
}
