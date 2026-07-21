package dev.mcbookshelf.ward;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.stream.Stream;

/**
 * Records system messages sent to players so chat assertions can check them. Each test remembers
 * the last sequence number it has seen, so concurrent tests do not consume each other's messages.
 */
public final class ChatRecorder {
	private static final int RETENTION_TICKS = 2;

	private record Message(UUID recipient, long sequence, long time, String text) {
	}

	private static final List<Message> MESSAGES = new ArrayList<>();
	private static long sequence = 0;

	private ChatRecorder() {
	}

	public static void record(UUID recipient, long gameTime, String text) {
		MESSAGES.removeIf(message -> message.time() < gameTime - RETENTION_TICKS);
		MESSAGES.add(new Message(recipient, ++sequence, gameTime, text));
	}

	public static void clear() {
		MESSAGES.clear();
	}

	public static long sequence() {
		return sequence;
	}

	public static Stream<String> since(long sequence) {
		return MESSAGES.stream().filter(message -> message.sequence() > sequence).map(Message::text);
	}

	public static Stream<String> since(long sequence, UUID recipient) {
		return MESSAGES.stream().filter(message -> message.sequence() > sequence && message.recipient().equals(recipient)).map(Message::text);
	}
}
