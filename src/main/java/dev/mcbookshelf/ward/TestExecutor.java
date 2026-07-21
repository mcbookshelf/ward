package dev.mcbookshelf.ward;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.Queue;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Supplier;
import java.util.stream.Stream;

import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.mojang.brigadier.exceptions.SimpleCommandExceptionType;
import org.jspecify.annotations.Nullable;

import net.minecraft.commands.CommandResultCallback;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.coordinates.Coordinates;
import net.minecraft.commands.execution.ExecutionContext;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.gametest.framework.GameTestInfo;
import net.minecraft.gametest.framework.GameTestListener;
import net.minecraft.gametest.framework.GameTestRunner;
import net.minecraft.network.chat.Component;
import net.minecraft.server.players.PlayerList;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec2;
import net.minecraft.world.phys.Vec3;

import dev.mcbookshelf.ward.dummy.Dummy;

/**
 * Runs test commands in order, pausing while awaits are pending. The test succeeds once every
 * command and await has completed.
 */
public class TestExecutor {
	private static final SimpleCommandExceptionType ERROR_NOT_IN_TEST = new SimpleCommandExceptionType(
			Component.translatable("ward.not_in_test"));

	private static @Nullable TestExecutor current;

	private final List<Supplier<Boolean>> awaits = new ArrayList<>();
	private final List<Dummy> dummies = new ArrayList<>();
	private final GameTestHelper helper;
	private final int timeout;
	private long chatSequence = ChatRecorder.sequence();
	private int line = 0;
	private boolean done = false;

	public TestExecutor(GameTestHelper helper, int timeout) {
		this.helper = helper;
		this.timeout = timeout;
		helper.testInfo.addListener(new DummyCleanup());
	}

	public static TestExecutor current() throws CommandSyntaxException {
		if (current == null) throw ERROR_NOT_IN_TEST.create();
		return current;
	}

	public static void trackDummy(Dummy dummy) {
		if (current != null) {
			current.dummies.add(dummy);
		}
	}

	public void run(TestFunction function) {
		CommandSourceStack sender = createCommandSourceStack(function);
		Queue<TestFunction.Entry> commands = new ArrayDeque<>(function.commands());

		Runnable tick = () -> {
			current = this;

			try {
				if (!this.awaits.isEmpty() && this.awaits.getFirst().get()) {
					this.awaits.removeFirst();
				}

				while (!commands.isEmpty() && !this.done && this.awaits.isEmpty()) {
					TestFunction.Entry entry = commands.poll();
					this.line = entry.line();
					Commands.executeCommandInContext(sender, ctx ->
							ExecutionContext.queueInitialCommandExecution(
									ctx,
									entry.command(),
									entry.chain(),
									sender,
									CommandResultCallback.EMPTY));
				}

				if (!this.done && this.awaits.isEmpty()) {
					succeed();
				}
			} finally {
				current = null;
				this.chatSequence = ChatRecorder.sequence();
			}
		};

		this.helper.onEachTick(tick);
		this.helper.runAtTickTime(this.timeout, tick);
	}

	public void fail(Component message) {
		this.done = true;
		throw failure(message);
	}

	public void succeed() {
		this.done = true;
		this.helper.succeed();
	}

	public void await(int delay) {
		AtomicInteger remaining = new AtomicInteger(delay);
		this.awaits.add(() -> {
			if (remaining.decrementAndGet() <= 0) return true;
			// Fail early, with this delay's line, once the delay can no
			// longer finish before the timeout
			if (this.helper.getTick() + remaining.get() <= this.timeout) return false;
			throw failure(Component.translatable("ward.timeout", this.timeout));
		});
	}

	/**
	 * Asserts a condition immediately. The plain form expects at least one match, the negated
	 * form expects none (and no error).
	 */
	public int assertThat(AssertResult result, boolean negated) {
		if (satisfied(result, negated)) return negated ? 1 : result.count();
		fail(result.message().apply(negated));
		return 0;
	}

	public int assertThat(Supplier<AssertResult> check, boolean negated) {
		return assertThat(check.get(), negated);
	}

	/**
	 * Awaits a condition, retrying every tick until it is satisfied or the test times out. A check
	 * that errors counts as unsatisfied and keeps polling.
	 */
	public void awaitThat(Supplier<AssertResult> check, boolean negated) {
		awaitThat(check.get(), negated, check);
	}

	public void awaitThat(AssertResult first, boolean negated, Supplier<AssertResult> check) {
		if (satisfied(first, negated)) return;
		registerPoll(check, negated);
	}

	/**
	 * A plain check passes with a positive count, a negated check with a clean zero count.
	 */
	private boolean satisfied(AssertResult result, boolean negated) {
		return negated ? result.count() == 0 && !result.errored() : result.count() > 0;
	}

	/**
	 * Registers a pending condition. It retries every tick and fails with the check's message on
	 * the last tick before the timeout.
	 */
	private void registerPoll(Supplier<AssertResult> check, boolean negated) {
		this.awaits.add(() -> {
			AssertResult retry = check.get();
			if (satisfied(retry, negated)) return true;
			if (!isLastTick()) return false;
			throw failure(retry.message().apply(negated));
		});
	}

	private TestException failure(Component message) {
		return new TestException(message, this.line, this.helper.getTick());
	}

	private boolean isLastTick() {
		return this.helper.getTick() + 1 >= this.timeout;
	}

	public AABB getBounds() {
		return this.helper.getBounds();
	}

	public Stream<String> chatMessages() {
		return ChatRecorder.since(this.chatSequence);
	}

	public Stream<String> chatMessages(UUID recipient) {
		return ChatRecorder.since(this.chatSequence, recipient);
	}

	private CommandSourceStack createCommandSourceStack(TestFunction function) {
		// The server source stack defaults to the respawn dimension (the
		// overworld), so tests declaring @dimension must rebind their level
		CommandSourceStack source = this.helper.getLevel()
				.getServer()
				.createCommandSourceStack()
				.withLevel(this.helper.getLevel())
				.withPosition(this.helper.absoluteVec(Vec3.ZERO))
				.withSuppressedOutput();

		Optional<Coordinates> coordinates = function.directives().dummy();

		if (coordinates.isPresent()) {
			try {
				Vec3 pos = coordinates.get().getPosition(source);
				Vec2 rot = coordinates.get().getRotation(source);
				Dummy dummy = Dummy.create(helper.getLevel(), pos, rot);
				dummy.setOnGround(true);
				this.dummies.add(dummy);
				source = source.withEntity(dummy);
			} catch (IllegalArgumentException e) {
				this.helper.fail(Component.literal("Failed to initialize test with dummy"));
			}
		}

		return source;
	}

	/**
	 * Removes the dummies spawned by this test once it finishes, pass or fail.
	 */
	private final class DummyCleanup implements GameTestListener {
		@Override
		public void testStructureLoaded(GameTestInfo testInfo) {
		}

		@Override
		public void testPassed(GameTestInfo testInfo, GameTestRunner runner) {
			removeDummies();
		}

		@Override
		public void testFailed(GameTestInfo testInfo, GameTestRunner runner) {
			removeDummies();
		}

		@Override
		public void testAddedForRerun(GameTestInfo original, GameTestInfo copy, GameTestRunner runner) {
		}

		private void removeDummies() {
			PlayerList players = TestExecutor.this.helper.getLevel().getServer().getPlayerList();

			for (Dummy dummy : TestExecutor.this.dummies) {
				if (players.getPlayer(dummy.getUUID()) instanceof Dummy connected) {
					connected.leave(Component.literal("Test finished"));
				}
			}

			TestExecutor.this.dummies.clear();
		}
	}
}
