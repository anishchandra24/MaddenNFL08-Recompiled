// startup_checks.h - makes the port explain problems instead of closing silently.
//
//  - If no --game_data_root is given, use the "assets" folder next to the
//    install (so starting madden08.exe directly, or from a launcher, works).
//  - Warn when default.xex is not the version this port was made from.
//  - Pick a graphics card that supports rasterizer-ordered views (ROV); without
//    them the menus are black. Warn if no card has them.
//  - On a crash, write a crash report next to the logs and say where it is.
//  - If the program closes before the game started, say where the log is.
#pragma once

#ifdef _WIN32

#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <string>
#include <system_error>
#include <vector>

#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <bcrypt.h>
#include <d3d12.h>
#include <dxgi1_4.h>
#pragma comment(lib, "bcrypt.lib")
#pragma comment(lib, "d3d12.lib")
#pragma comment(lib, "dxgi.lib")

#include <rex/cvar.h>
#include <rex/filesystem.h>
#include <rex/logging.h>
#include <rex/logging/api.h>

namespace startup_checks {

inline constexpr char kExpectedXexSha256[] =
    "962EA344FB966E1BE1C94667D4213A309A69A821AE3BEC0CB2FCA4166ECC6627";
inline constexpr wchar_t kTitle[] = L"Madden NFL 08 Recompiled";
inline constexpr wchar_t kIssuesUrl[] =
    L"https://github.com/anishchandra24/MaddenNFL08-Recompiled/issues";

inline std::atomic<bool> g_game_started{false};
inline std::atomic<bool> g_message_shown{false};

inline std::filesystem::path LogDir() {
  return rex::filesystem::GetExecutableFolder() / "logs";
}

// SHA-256 of a file as uppercase hex, or an empty string on failure.
inline std::string Sha256File(const std::filesystem::path& path) {
  std::ifstream file(path, std::ios::binary);
  if (!file) {
    return {};
  }
  BCRYPT_ALG_HANDLE alg = nullptr;
  if (!BCRYPT_SUCCESS(BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, nullptr, 0))) {
    return {};
  }
  std::string result;
  BCRYPT_HASH_HANDLE hash = nullptr;
  if (BCRYPT_SUCCESS(BCryptCreateHash(alg, &hash, nullptr, 0, nullptr, 0, 0))) {
    std::vector<char> buffer(1 << 20);
    bool ok = true;
    while (file) {
      file.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
      std::streamsize got = file.gcount();
      if (got > 0 &&
          !BCRYPT_SUCCESS(BCryptHashData(hash, reinterpret_cast<PUCHAR>(buffer.data()),
                                         static_cast<ULONG>(got), 0))) {
        ok = false;
        break;
      }
    }
    UCHAR digest[32];
    if (ok && BCRYPT_SUCCESS(BCryptFinishHash(hash, digest, sizeof(digest), 0))) {
      static const char kHex[] = "0123456789ABCDEF";
      for (UCHAR b : digest) {
        result += kHex[b >> 4];
        result += kHex[b & 15];
      }
    }
    BCryptDestroyHash(hash);
  }
  BCryptCloseAlgorithmProvider(alg, 0);
  return result;
}

// Ends the program after a message the player chose not to continue past.
[[noreturn]] inline void QuitQuietly() {
  g_message_shown = true;
  rex::FlushLogging();
  std::exit(0);
}

// Use <install folder>\assets when no game folder was given.
inline void DefaultGameFolder(std::filesystem::path& game_data_root) {
  if (!game_data_root.empty()) {
    return;
  }
  std::error_code ec;
  std::filesystem::path assets = rex::filesystem::GetExecutableFolder().parent_path() / "assets";
  if (std::filesystem::is_directory(assets, ec)) {
    game_data_root = assets;
    REXLOG_INFO("startup: no --game_data_root given, using {}", assets.string());
  }
}

// Warn when default.xex is not the version this port was generated from.
inline void CheckGameVersion(const std::filesystem::path& game_data_root) {
  if (game_data_root.empty()) {
    return;  // the SDK shows its own message
  }
  std::error_code ec;
  std::filesystem::path xex = game_data_root / "default.xex";
  if (!std::filesystem::is_regular_file(xex, ec)) {
    return;  // the SDK shows its own message
  }
  std::string hash = Sha256File(xex);
  if (hash.empty()) {
    REXLOG_WARN("startup: could not read {} to check its version", xex.string());
    return;
  }
  if (hash == kExpectedXexSha256) {
    REXLOG_INFO("startup: default.xex is the supported version");
    return;
  }
  REXLOG_WARN("startup: default.xex is NOT the supported version (SHA-256 {})", hash);
  std::wstring msg =
      L"Your game's default.xex is not the version this port was made from.\n\n"
      L"Found: " + xex.wstring() + L"\n\n"
      L"A different release or region of the game will most likely crash or "
      L"misbehave. If you extracted the game from an ISO, check that the "
      L"extraction finished.\n\nStart anyway?";
  if (MessageBoxW(nullptr, msg.c_str(), kTitle, MB_YESNO | MB_ICONWARNING | MB_TOPMOST) != IDYES) {
    QuitQuietly();
  }
}

// Make sure the graphics card in use supports rasterizer-ordered views. If the
// card Windows lists first does not but another one does, switch to it.
inline void CheckGraphicsCard() {
  IDXGIFactory1* factory = nullptr;
  if (FAILED(CreateDXGIFactory1(IID_PPV_ARGS(&factory)))) {
    REXLOG_WARN("startup: could not list the graphics cards");
    return;
  }
  bool user_chose = rex::cvar::GetFlagSource("d3d12_adapter") != rex::cvar::Source::kDefault;
  int user_choice = user_chose ? std::atoi(rex::cvar::GetFlagByName("d3d12_adapter").c_str()) : -1;
  if (user_choice < 0) {
    user_chose = false;
  }
  int chosen = -1;
  bool chosen_rov = false;
  std::wstring chosen_name;
  int first_rov = -1;
  std::wstring first_rov_name;
  IDXGIAdapter1* adapter = nullptr;
  for (UINT i = 0; factory->EnumAdapters1(i, &adapter) == S_OK; ++i) {
    DXGI_ADAPTER_DESC1 desc = {};
    adapter->GetDesc1(&desc);
    bool usable = false;
    bool rov = false;
    if (!(desc.Flags & DXGI_ADAPTER_FLAG_SOFTWARE)) {
      ID3D12Device* device = nullptr;
      if (SUCCEEDED(D3D12CreateDevice(adapter, D3D_FEATURE_LEVEL_11_0, IID_PPV_ARGS(&device)))) {
        usable = true;
        D3D12_FEATURE_DATA_D3D12_OPTIONS options = {};
        if (SUCCEEDED(device->CheckFeatureSupport(D3D12_FEATURE_D3D12_OPTIONS, &options,
                                                  sizeof(options)))) {
          rov = options.ROVsSupported != FALSE;
        }
        device->Release();
      }
    }
    adapter->Release();
    adapter = nullptr;
    if (!usable) {
      continue;
    }
    std::wstring name = desc.Description;
    REXLOG_INFO("startup: graphics card {}: {} (ROV {})", i,
                std::filesystem::path(name).string(), rov ? "yes" : "no");
    bool is_chosen = user_chose ? (int(i) == user_choice) : (chosen < 0);
    if (is_chosen && chosen < 0) {
      chosen = int(i);
      chosen_rov = rov;
      chosen_name = name;
    }
    if (rov && first_rov < 0) {
      first_rov = int(i);
      first_rov_name = name;
    }
  }
  factory->Release();

  if (chosen < 0 || chosen_rov) {
    return;  // nothing usable found (the SDK reports it), or the card is fine
  }
  if (!user_chose && first_rov >= 0) {
    std::string index = std::to_string(first_rov);
    if (rex::cvar::SetFlagByName("d3d12_adapter", index)) {
      REXLOG_WARN("startup: card {} has no ROV support; switched to card {} ({})", chosen, first_rov,
                  std::filesystem::path(first_rov_name).string());
      return;
    }
    REXLOG_WARN("startup: could not switch to card {}", first_rov);
  }
  std::wstring msg = L"The graphics card in use (" + chosen_name +
                     L") does not support rasterizer-ordered views, which this port needs. "
                     L"The game will most likely show a black screen.\n\n";
  if (first_rov >= 0) {
    msg += L"Another graphics card in this PC supports them: " + first_rov_name +
           L". To use it, add --d3d12_adapter=" + std::to_wstring(first_rov) +
           L" to the shortcut's Target.\n\n";
  }
  msg += L"Start anyway?";
  if (MessageBoxW(nullptr, msg.c_str(), kTitle, MB_YESNO | MB_ICONWARNING | MB_TOPMOST) != IDYES) {
    QuitQuietly();
  }
}

inline LONG WINAPI CrashFilter(EXCEPTION_POINTERS* info) {
  if (g_message_shown.exchange(true)) {
    return EXCEPTION_EXECUTE_HANDLER;
  }
  DWORD code = 0;
  void* address = nullptr;
  if (info && info->ExceptionRecord) {
    code = info->ExceptionRecord->ExceptionCode;
    address = info->ExceptionRecord->ExceptionAddress;
  }
  char module_path[MAX_PATH] = "unknown";
  unsigned long long offset = 0;
  HMODULE module = nullptr;
  if (address && GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                                        GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                                    static_cast<LPCSTR>(address), &module)) {
    GetModuleFileNameA(module, module_path, MAX_PATH);
    offset = reinterpret_cast<uintptr_t>(address) - reinterpret_cast<uintptr_t>(module);
  }
  REXLOG_ERROR("CRASH: exception {:08X} in {} at +{:X} (game started: {})", code, module_path,
               offset, g_game_started.load() ? "yes" : "no");
  rex::FlushLogging();

  std::error_code ec;
  std::filesystem::create_directories(LogDir(), ec);
  SYSTEMTIME now;
  GetLocalTime(&now);
  char name[64];
  std::snprintf(name, sizeof(name), "crash_%04u%02u%02u_%02u%02u%02u.txt", now.wYear, now.wMonth,
                now.wDay, now.wHour, now.wMinute, now.wSecond);
  std::filesystem::path report = LogDir() / name;
  {
    std::ofstream out(report);
    char line[512];
    std::snprintf(line, sizeof(line),
                  "Madden NFL 08 Recompiled crash report\n"
                  "Exception code: 0x%08lX\nModule: %s\nOffset: 0x%llX\nGame started: %s\n",
                  static_cast<unsigned long>(code), module_path, offset,
                  g_game_started.load() ? "yes" : "no");
    out << line;
  }
  std::wstring msg = L"Madden NFL 08 Recompiled crashed.\n\n"
                     L"Please report it at\n" + std::wstring(kIssuesUrl) +
                     L"\nand attach these two files:\n" + report.wstring() +
                     L"\nand the newest madden08_###.log in the same folder.";
  MessageBoxW(nullptr, msg.c_str(), kTitle, MB_OK | MB_ICONERROR | MB_TOPMOST);
  return EXCEPTION_EXECUTE_HANDLER;
}

inline void ExitCheck() {
  if (g_game_started || g_message_shown) {
    return;
  }
  rex::FlushLogging();
  std::wstring msg = L"Madden NFL 08 Recompiled closed before the game started.\n\n"
                     L"The log file may say why. If you report it at\n" +
                     std::wstring(kIssuesUrl) +
                     L"\nplease attach the newest madden08_###.log from:\n" + LogDir().wstring();
  MessageBoxW(nullptr, msg.c_str(), kTitle, MB_OK | MB_ICONWARNING | MB_TOPMOST);
}

// Test helper: MADDEN08_TEST_CRASH=1 crashes on purpose once the game starts,
// to check that the crash report appears. Does nothing when it is not set.
inline void MaybeTestCrash() {
  const char* v = std::getenv("MADDEN08_TEST_CRASH");
  if (v && *v == '1') {
    REXLOG_WARN("startup: MADDEN08_TEST_CRASH is set, crashing on purpose");
    *static_cast<volatile int*>(nullptr) = 0;
  }
}

inline void InstallHandlers() {
  static bool installed = false;
  if (installed) {
    return;
  }
  installed = true;
  SetUnhandledExceptionFilter(CrashFilter);
  std::atexit(ExitCheck);
}

}  // namespace startup_checks

#endif  // _WIN32
