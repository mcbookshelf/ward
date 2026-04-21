package dev.mcbookshelf.ward;

import dev.mcbookshelf.ward.accessor.TestContextAccessor;
import dev.mcbookshelf.ward.dummy.Dummy;
import net.minecraft.commands.CommandResultCallback;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.coordinates.Coordinates;
import net.minecraft.commands.execution.ExecutionContext;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.network.chat.Component;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec2;
import net.minecraft.world.phys.Vec3;

import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Function;
import java.util.function.Supplier;

/**
 * Executes test commands and manages asynchronous await conditions.
 * <p>
 * Commands execute sequentially, pausing when awaits are encountered.
 */
public class TestContext {

    private final List<Supplier<Boolean>> awaits;
    private final GameTestHelper helper;
    private final int timeout;
    private int line = 0;
    private boolean done = false;

    /**
     * Result of an assertion check.
     *
     * @param count number of matching items (>0 indicates condition met)
     * @param message builder function that creates error messages based on negation state
     */
    public record AssertResult(int count, Function<Boolean, Component> message) {}

    public TestContext(GameTestHelper helper, int timeout) {
        this.awaits = new ArrayList<>();
        this.helper = helper;
        this.timeout = timeout;
    }

    /**
     * Returns the axis-aligned bounding box representing the test structure bounds.
     */
    public AABB getBounds() {
        return this.helper.getBounds();
    }

    /**
     * Immediately fails the test with the given message.
     */
    public void fail(Component message) {
        this.done = true;
        throw new TestException(message, this.line, this.helper.getTick());
    }

    /**
     * Immediately succeeds the test and stops execution.
     */
    public void succeed() {
        this.done = true;
        this.helper.succeed();
    }

    /**
     * Asserts that a condition is true (count > 0).
     * Fails immediately if the check returns 0.
     *
     * @return the count from the check
     */
    public int assertTrue(Supplier<AssertResult> check) {
        AssertResult result = check.get();
        if (result.count > 0) return result.count;
        fail(result.message.apply(false));
        return 0;
    }

    /**
     * Asserts that a condition is false (count == 0).
     * Fails immediately if the check returns > 0.
     *
     * @return 1 if the check passed (count was 0)
     */
    public int assertFalse(Supplier<AssertResult> check) {
        AssertResult result = check.get();
        if (result.count == 0) return 1;
        fail(result.message.apply(true));
        return 0;
    }

    /**
     * Awaits a condition to become true (count > 0).
     * Tries immediately, then retries every tick until timeout.
     */
    public void awaitTrue(Supplier<AssertResult> check) {
        AssertResult result = check.get();
        if (result.count > 0) return;

        this.awaits.add(() -> {
            AssertResult retry = check.get();
            if (retry.count > 0) return true;
            if (this.helper.getTick() < this.timeout) return false;
            throw new TestException(
                retry.message.apply(false),
                this.line,
                this.helper.getTick()
            );
        });
    }

    /**
     * Awaits a condition to become false (count == 0).
     * Tries immediately, then retries every tick until timeout.
     */
    public void awaitFalse(Supplier<AssertResult> check) {
        AssertResult result = check.get();
        if (result.count == 0) return;

        this.awaits.add(() -> {
            AssertResult retry = check.get();
            if (retry.count == 0) return true;
            if (this.helper.getTick() < this.timeout) return false;
            throw new TestException(
                retry.message.apply(true),
                this.line,
                this.helper.getTick()
            );
        });
    }

    /**
     * Queues a delay for the specified number of ticks.
     * Test execution pauses until the delay completes.
     *
     * @param delay number of ticks to wait
     */
    public void await(int delay) {
        AtomicInteger remaining = new AtomicInteger(delay);
        this.awaits.add(() -> {
            if (remaining.decrementAndGet() <= 0) return true;
            if (this.helper.getTick() < this.timeout) return false;
            this.done = true;
            throw new TestException(
                Component.translatable("ward.timeout", this.timeout),
                this.line,
                this.helper.getTick()
            );
        });
    }

    public void run(TestFunction function) {
        CommandSourceStack sender = createCommandSourceStack(function);
        Queue<TestFunction.Entry> commands = new ArrayDeque<>(function.commands());

        this.helper.onEachTick(() -> {
            // Check if the first await condition is satisfied
            if (!this.awaits.isEmpty() && this.awaits.getFirst().get()) {
                this.awaits.removeFirst();
            }
            // Execute commands while no awaits are blocking
            while (!commands.isEmpty() && !this.done && this.awaits.isEmpty()) {
                TestFunction.Entry entry = commands.poll();
                this.line = entry.line();
                // Inject context so /fail, /await, /assert commands can access it
                ((TestContextAccessor) sender).ward$setContext(this);
                Commands.executeCommandInContext(sender, ctx ->
                    ExecutionContext.queueInitialCommandExecution(
                        ctx,
                        entry.command(),
                        entry.chain(),
                        sender,
                        CommandResultCallback.EMPTY));
            }
            // If all commands and awaits complete, test succeeds
            if (this.awaits.isEmpty()) {
                this.helper.succeed();
            }

            ChatRecorder.clear();
        });
    }

    private CommandSourceStack createCommandSourceStack(TestFunction function) {
        CommandSourceStack source = this.helper.getLevel().getServer().createCommandSourceStack()
            .withPosition(this.helper.absoluteVec(Vec3.ZERO))
            .withSuppressedOutput();

        Optional<Coordinates> coordinates = function.directives().dummy();
        if (coordinates.isPresent()) {
            try {
                Vec3 pos = coordinates.get().getPosition(source);
                Vec2 rot = coordinates.get().getRotation(source);
                Dummy dummy = Dummy.create(helper.getLevel(), pos, rot);
                dummy.setOnGround(true);
                source = source.withEntity(dummy);
            } catch (IllegalArgumentException e) {
                this.helper.fail(Component.literal("Failed to initialize test with dummy"));
            }
        }

        return source;
    }
}
