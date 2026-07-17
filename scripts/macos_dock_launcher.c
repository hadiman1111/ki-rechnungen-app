/*
 * Native macOS Dock-App stub for KI-Rechnungen.
 * Paths are injected at build time via -D macros.
 * Starts app_internal_launcher.py (same entry as run_internal_launcher_flet085.sh).
 * No automatic invoice processing.
 */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#ifndef PROJECT_ROOT
#error "PROJECT_ROOT must be defined at compile time"
#endif
#ifndef PYTHON_BIN
#error "PYTHON_BIN must be defined at compile time"
#endif
#ifndef ENTRY_PY
#error "ENTRY_PY must be defined at compile time"
#endif

static void ensure_log_dir(char *log_file, size_t log_file_size) {
  const char *home = getenv("HOME");
  if (home == NULL || home[0] == '\0') {
    home = ".";
  }
  snprintf(log_file, log_file_size, "%s/Library/Logs/KI-Rechnungen", home);
  mkdir(log_file, 0755);
  snprintf(log_file, log_file_size, "%s/Library/Logs/KI-Rechnungen/dock-app.log", home);
}

static void append_log(const char *log_file, const char *message) {
  FILE *fp = fopen(log_file, "a");
  if (fp == NULL) {
    return;
  }
  time_t now = time(NULL);
  struct tm tm_now;
  localtime_r(&now, &tm_now);
  char ts[32];
  strftime(ts, sizeof(ts), "%Y-%m-%dT%H:%M:%S", &tm_now);
  fprintf(fp, "[%s] %s\n", ts, message);
  fclose(fp);
}

static void show_alert(const char *message) {
  char cmd[1024];
  snprintf(
      cmd,
      sizeof(cmd),
      "osascript -e 'display alert \"KI-Rechnungen\" message \"%s\" as critical' >/dev/null 2>&1",
      message);
  system(cmd);
}

int main(void) {
  char log_file[512];
  char line[1024];

  ensure_log_dir(log_file, sizeof(log_file));
  append_log(log_file, "KI-Rechnungen Dock-App Start (native stub)");
  snprintf(line, sizeof(line), "PROJECT_ROOT=%s", PROJECT_ROOT);
  append_log(log_file, line);
  snprintf(line, sizeof(line), "PYTHON_BIN=%s", PYTHON_BIN);
  append_log(log_file, line);
  snprintf(line, sizeof(line), "ENTRY_PY=%s", ENTRY_PY);
  append_log(log_file, line);

  if (chdir(PROJECT_ROOT) != 0) {
    append_log(log_file, "FEHLER: chdir PROJECT_ROOT fehlgeschlagen");
    show_alert("Projektverzeichnis nicht gefunden. Bitte die App neu bauen.");
    return 1;
  }

  if (access(PYTHON_BIN, X_OK) != 0) {
    append_log(log_file, "FEHLER: Python nicht ausfuehrbar");
    show_alert(".venv-flet085 fehlt. Bitte Build-Umgebung herstellen.");
    return 1;
  }

  if (access(ENTRY_PY, R_OK) != 0) {
    append_log(log_file, "FEHLER: app_internal_launcher.py nicht lesbar");
    show_alert("app_internal_launcher.py fehlt.");
    return 1;
  }

  setenv("PYTHONPATH", PROJECT_ROOT, 1);

  int log_fd = open(log_file, O_WRONLY | O_CREAT | O_APPEND, 0644);
  if (log_fd >= 0) {
    dup2(log_fd, STDOUT_FILENO);
    dup2(log_fd, STDERR_FILENO);
    close(log_fd);
  }

  append_log(log_file, "Starte internen Launcher via Python-Entry (kein Auto-Lauf)");
  execl(PYTHON_BIN, PYTHON_BIN, ENTRY_PY, (char *)NULL);

  snprintf(line, sizeof(line), "FEHLER: execl fehlgeschlagen: %s", strerror(errno));
  append_log(log_file, line);
  show_alert("Launcher konnte nicht gestartet werden. Details im Log.");
  return 1;
}
