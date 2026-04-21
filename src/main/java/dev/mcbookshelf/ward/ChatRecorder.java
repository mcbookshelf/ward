package dev.mcbookshelf.ward;

import java.util.*;

public final class ChatRecorder {

    private static final Map<UUID, List<String>> messages = new HashMap<>();

    public static void clear() {
        messages.clear();
    }

    public static List<String> get() {
        return messages.values().stream().flatMap(List::stream).toList();
    }

    public static List<String> get(UUID id) {
        return messages.getOrDefault(id, List.of());
    }

    public static void record(UUID id, String message) {
        messages.computeIfAbsent(id, _ -> new ArrayList<>()).add(message);
    }
}
