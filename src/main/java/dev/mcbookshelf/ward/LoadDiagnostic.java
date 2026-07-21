package dev.mcbookshelf.ward;

/**
 * A datapack file that failed to load, with the registry kind and resource id it belongs to.
 */
public record LoadDiagnostic(Severity severity, String type, String id, String message) {
	public enum Severity {
		ERROR, WARN
	}

	public static LoadDiagnostic error(String type, String id, String message) {
		return new LoadDiagnostic(Severity.ERROR, type, id, message);
	}

	public static LoadDiagnostic warn(String type, String id, String message) {
		return new LoadDiagnostic(Severity.WARN, type, id, message);
	}

	public static String describe(Throwable error) {
		String message = error.getMessage();
		return message == null
				? error.getClass().getSimpleName()
				: message.replaceFirst("^[A-Za-z0-9.$]+(Exception|Error): ", "");
	}
}
