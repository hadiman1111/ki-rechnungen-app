/*
 * Bootstrap for the bundled FletView (de.kirechnungen.view).
 *
 * macOS pins the visible FletView in the Dock. A cold Dock click would otherwise
 * start only the Flutter client without Python → empty light-blue window.
 *
 * - Warm start (Flet passes page_url + pid_file): exec the real Flutter binary.
 * - Cold start (Dock / Finder, no page args): open the outer KI-Rechnungen.app
 *   stub, which starts app_internal_launcher.py (no automatic invoice processing).
 */
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <mach-o/dyld.h>
#include <spawn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

extern char **environ;

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

static int resolve_self_dir(char *out, size_t out_size) {
  char exe[PATH_MAX];
  uint32_t size = sizeof(exe);
  if (_NSGetExecutablePath(exe, &size) != 0) {
    return -1;
  }

  char resolved[PATH_MAX];
  if (realpath(exe, resolved) != NULL) {
    strncpy(exe, resolved, sizeof(exe) - 1);
    exe[sizeof(exe) - 1] = '\0';
  }

  char *slash = strrchr(exe, '/');
  if (slash == NULL) {
    return -1;
  }
  *slash = '\0';

  if (strlen(exe) + 1 > out_size) {
    return -1;
  }
  memcpy(out, exe, strlen(exe) + 1);
  return 0;
}

/* .../Outer.app/Contents/Resources/FletView/Inner.app/Contents/MacOS → Outer.app */
static int resolve_outer_app(const char *macos_dir, char *out, size_t out_size) {
  char path[PATH_MAX];
  if (strlen(macos_dir) + 1 > sizeof(path)) {
    return -1;
  }
  memcpy(path, macos_dir, strlen(macos_dir) + 1);

  char *marker = strstr(path, "/FletView/");
  if (marker == NULL) {
    return -1;
  }
  *marker = '\0'; /* .../Outer.app/Contents/Resources */

  char *slash = strrchr(path, '/');
  if (slash == NULL) {
    return -1;
  }
  *slash = '\0'; /* .../Outer.app/Contents */

  slash = strrchr(path, '/');
  if (slash == NULL) {
    return -1;
  }
  *slash = '\0'; /* .../Outer.app */

  if (strlen(path) + 1 > out_size) {
    return -1;
  }
  memcpy(out, path, strlen(path) + 1);
  return 0;
}

static int is_warm_flet_launch(int argc, char **argv) {
  /*
   * Flet 0.85 macOS: open … --args <page_url> <pid_file> [assets_dir]
   * page_url is often a temp path under /var/folders (not http://).
   * Cold Dock/Finder launches have argc == 1.
   */
  (void)argv;
  return argc >= 3;
}

int main(int argc, char **argv) {
  char log_file[512];
  char line[1024];
  char macos_dir[PATH_MAX];
  char real_bin[PATH_MAX];
  char outer_app[PATH_MAX];

  ensure_log_dir(log_file, sizeof(log_file));

  if (resolve_self_dir(macos_dir, sizeof(macos_dir)) != 0) {
    append_log(log_file, "FEHLER: FletView-Bootstrap: eigener Pfad unbekannt");
    return 1;
  }

  int n = snprintf(real_bin, sizeof(real_bin), "%s/ki-rechnungen-app.real", macos_dir);
  if (n < 0 || (size_t)n >= sizeof(real_bin)) {
    append_log(log_file, "FEHLER: FletView-Bootstrap: Real-Binary-Pfad zu lang");
    return 1;
  }

  if (is_warm_flet_launch(argc, argv)) {
    append_log(log_file, "FletView-Bootstrap: Warm-Start (page_url) → Real-Binary");
    execv(real_bin, argv);
    snprintf(line, sizeof(line), "FEHLER: execv Real-Binary: %s", strerror(errno));
    append_log(log_file, line);
    return 1;
  }

  /* Cold Dock/Finder launch: do not open empty Flutter UI. */
  append_log(log_file, "FletView-Bootstrap: Kaltstart (Dock) → Outer-App öffnen");
  if (resolve_outer_app(macos_dir, outer_app, sizeof(outer_app)) != 0) {
    append_log(log_file, "FEHLER: Outer KI-Rechnungen.app nicht auflösbar");
    return 1;
  }
  snprintf(line, sizeof(line), "OUTER_APP=%s", outer_app);
  append_log(log_file, line);

  {
    struct stat st;
    if (stat(outer_app, &st) != 0 || !S_ISDIR(st.st_mode)) {
      append_log(log_file, "FEHLER: Outer-App fehlt");
      return 1;
    }
  }

  pid_t child = 0;
  char *open_argv[] = {"/usr/bin/open", outer_app, NULL};
  int rc = posix_spawn(&child, "/usr/bin/open", NULL, NULL, open_argv, environ);
  if (rc != 0) {
    snprintf(line, sizeof(line), "FEHLER: posix_spawn open Outer: %s", strerror(rc));
    append_log(log_file, line);
    return 1;
  }
  snprintf(line, sizeof(line), "Outer-App gestartet via open (pid=%d)", (int)child);
  append_log(log_file, line);
  return 0;
}
