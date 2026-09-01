package dev.mcbookshelf.ward;

public record LoadDiagnostic(Severity severity, String kind, String id, String message) {
	public enum Severity {
		ERROR, WARN
	}

	public static LoadDiagnostic error(String kind, String id, String message) {
		return new LoadDiagnostic(Severity.ERROR, kind, id, message);
	}

	public static LoadDiagnostic warn(String kind, String id, String message) {
		return new LoadDiagnostic(Severity.WARN, kind, id, message);
	}

	public static String describe(Throwable error) {
		String message = error.getMessage();
		return message == null
				? error.getClass().getSimpleName()
				: message.replaceFirst("^[A-Za-z0-9.$]+(Exception|Error): ", "");
	}
}
