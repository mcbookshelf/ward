package dev.mcbookshelf.ward.test;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.UUID;
import java.util.stream.Stream;

import org.jspecify.annotations.Nullable;

import net.minecraft.util.Util;

public final class ChatRecorder {
	private static final int RETENTION_LIMIT = 4096;
	private static final Deque<Message> MESSAGES = new ArrayDeque<>();
	private static long sequence;
	private static boolean broadcasting;

	private record Message(
			UUID recipient,
			long sequence,
			String text,
			boolean echo,
			@Nullable TestExecutor test) {
	}

	private ChatRecorder() {
	}

	public static void clear() {
		MESSAGES.clear();
	}

	public static long sequence() {
		return sequence;
	}

	public static Stream<String> since(long sequence, TestExecutor test) {
		return visible(sequence, test).filter(message -> !message.echo()).map(Message::text);
	}

	public static Stream<String> since(long sequence, TestExecutor test, UUID recipient) {
		return visible(sequence, test).filter(message -> message.recipient().equals(recipient)).map(Message::text);
	}

	private static Stream<Message> visible(long sequence, TestExecutor test) {
		return MESSAGES.stream().filter(message -> message.sequence() > sequence && (message.test() == null || message.test() == test));
	}

	public static void record(UUID recipient, String text) {
		if (MESSAGES.size() >= RETENTION_LIMIT) {
			MESSAGES.removeFirst();
		}

		MESSAGES.add(new Message(recipient, ++sequence, text, broadcasting, TestExecutor.current));
	}

	public static void broadcast(String text, Runnable delivery) {
		record(Util.NIL_UUID, text);
		boolean outer = broadcasting;
		broadcasting = true;

		try {
			delivery.run();
		} finally {
			broadcasting = outer;
		}
	}
}
