// madden08 - ReXGlue Recompiled Project
//
// Customize your app by overriding virtual hooks from rex::ReXApp.

#pragma once

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

#include <rex/filesystem/devices/host_path_device.h>
#include <rex/filesystem/devices/null_device.h>
#include <rex/logging.h>
#include <rex/rex_app.h>
#include <rex/system/kernel_state.h>
#include <rex/system/xmemory.h>
#include <rex/system/util/xdbf_utils.h>
#include <rex/ui/window.h>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <timeapi.h>
#pragma comment(lib, "winmm.lib")
#pragma comment(lib, "user32.lib")
#endif

class Madden08App : public rex::ReXApp {
 public:
  using rex::ReXApp::ReXApp;

  static std::unique_ptr<rex::ui::WindowedApp> Create(
      rex::ui::WindowedAppContext& ctx) {
    return std::unique_ptr<Madden08App>(new Madden08App(ctx, "madden08",
        PPCImageConfig));
  }

#ifdef _WIN32
  // Frame pacing: the SDK's GPU vsync thread sleeps in 1 ms steps, but
  // Windows wakes threads only every ~15.6 ms unless a finer timer
  // resolution is requested. Ask for 1 ms for this process.
  void OnPreSetup(rex::RuntimeConfig& config) override {
    timeBeginPeriod(1);
  }
#endif

  // The window and the game's data may not both be ready at the first hook,
  // so each hook tries again until the work is done.
  void OnPostLoadXexImage() override { ApplyWindowExtras(); }
  void OnPostSetup() override {
    MountCacheDrives();
    ApplyWindowExtras();
  }
  void OnPreLaunchModule() override {
    DumpGuestImage();
    ApplyWindowExtras();
  }

 private:
  // Research helper: when MADDEN08_DUMP_IMAGE is set to a file path, write the
  // game's loaded memory image (code + data, as the game sees it) to that file
  // once, right before the game starts. A scanner script then finds every
  // function address the game's tables point at, so missing functions can be
  // added all at once. Does nothing when the variable is not set.
  void DumpGuestImage() {
    const char* path = std::getenv("MADDEN08_DUMP_IMAGE");
    if (!path || !*path) {
      return;
    }
    rex::Runtime* rt = runtime();
    if (!rt || !rt->memory()) {
      REXLOG_INFO("madden08: image dump skipped (no memory yet)");
      return;
    }
    const uint32_t base = PPCImageConfig.image_base;
    const uint32_t size = PPCImageConfig.image_size;
    REXLOG_INFO("madden08: image base {:08X} size {:08X} code base {:08X} code size {:08X}",
                base, size, PPCImageConfig.code_base, PPCImageConfig.code_size);
    const uint8_t* src = rt->memory()->TranslateVirtual<const uint8_t*>(base);
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out) {
      REXLOG_INFO("madden08: image dump could not open {}", path);
      return;
    }
    out.write(reinterpret_cast<const char*>(src), static_cast<std::streamsize>(size));
    out.close();
    REXLOG_INFO("madden08: image dump wrote {} bytes to {}", size, path);
  }
  bool cache_done_ = false;

  // Experiment for the "cache:" drive Madden NFL 08 asks for at startup.
  // Chosen with the MADDEN08_CACHE_MODE environment variable:
  //   0 (or unset) = do nothing (the SDK default)
  //   1 = add "cache:", "cache0:" and "cache1:" links that point at the SDK's
  //       existing (null) cache partitions
  //   2 = as 1, but back Cache0/Cache1 with real folders on this PC
  void MountCacheDrives() {
    if (cache_done_) {
      return;
    }
    rex::Runtime* rt = runtime();
    if (!rt || !rt->file_system()) {
      return;
    }
    cache_done_ = true;
    const char* env = std::getenv("MADDEN08_CACHE_MODE");
    int mode = env ? std::atoi(env) : 1;
    REXLOG_INFO("madden08: cache mode {}", mode);
    if (mode <= 0) {
      return;
    }
    rex::filesystem::VirtualFileSystem* vfs = rt->file_system();
    if (mode >= 2) {
      std::error_code ec;
      std::filesystem::path root = rt->cache_root();
      if (root.empty()) {
        root = std::filesystem::temp_directory_path(ec) / "madden08_cache";
      }
      std::filesystem::path c0 = root / "xbox_cache0";
      std::filesystem::path c1 = root / "xbox_cache1";
      std::filesystem::create_directories(c0, ec);
      std::filesystem::create_directories(c1, ec);
      // The SDK's null device owns everything under \Device\Harddisk0 and is
      // matched first, so swap it for real folders plus a null Partition0.
      vfs->UnregisterDevice("\\Device\\Harddisk0");
      auto d0 = std::make_unique<rex::filesystem::HostPathDevice>(
          "\\Device\\Harddisk0\\Cache0", c0, false);
      if (d0->Initialize()) {
        vfs->RegisterDevice(std::move(d0));
      }
      auto d1 = std::make_unique<rex::filesystem::HostPathDevice>(
          "\\Device\\Harddisk0\\Cache1", c1, false);
      if (d1->Initialize()) {
        vfs->RegisterDevice(std::move(d1));
      }
      auto nd = std::make_unique<rex::filesystem::NullDevice>(
          "\\Device\\Harddisk0", std::initializer_list<std::string>{"\\Partition0"});
      if (nd->Initialize()) {
        vfs->RegisterDevice(std::move(nd));
      }
      REXLOG_INFO("madden08: cache folders {} and {}", c0.string(), c1.string());
    }
    vfs->RegisterSymbolicLink("cache:", "\\Device\\Harddisk0\\Cache0");
    vfs->RegisterSymbolicLink("cache0:", "\\Device\\Harddisk0\\Cache0");
    vfs->RegisterSymbolicLink("cache1:", "\\Device\\Harddisk0\\Cache1");
  }

  bool cursor_done_ = false;
  bool icon_done_ = false;

  void ApplyWindowExtras() {
    rex::ui::Window* w = window();
    if (!w) {
      return;
    }
    if (!cursor_done_) {
      // Hide the mouse pointer after a short idle time; moving the mouse shows it again.
      w->SetCursorVisibility(rex::ui::Window::CursorVisibility::kAutoHidden);
      cursor_done_ = true;
    }
#ifdef _WIN32
    if (!icon_done_) {
      ApplyTitleIcon(w);
    }
#endif
  }

#ifdef _WIN32
  // Takes the game's own title icon (a PNG stored inside default.xex), wraps it
  // as madden08.ico next to the exe, and sets it as the window icon.
  void ApplyTitleIcon(rex::ui::Window* w) {
    HWND hwnd = static_cast<HWND>(w->GetNativeWindowHandle());
    if (!hwnd) {
      return;  // window not open yet; the next hook tries again
    }
    icon_done_ = true;  // only one real attempt
    if (!runtime() || !runtime()->kernel_state()) {
      REXLOG_WARN("icon: no kernel state yet");
      return;
    }
    auto db = runtime()->kernel_state()->title_xdbf();
    if (!db.is_valid()) {
      REXLOG_WARN("icon: no XDBF data in the game");
      return;
    }
    auto icon = db.icon();
    if (!icon || icon.size < 33) {
      REXLOG_WARN("icon: the game has no title icon");
      return;
    }
    const uint8_t* p = icon.buffer;
    static const uint8_t kPngSig[8] = {0x89, 'P', 'N', 'G', 0x0D, 0x0A, 0x1A, 0x0A};
    if (std::memcmp(p, kPngSig, 8) != 0) {
      REXLOG_WARN("icon: the title icon is not a PNG");
      return;
    }
    uint32_t width = (uint32_t(p[16]) << 24) | (uint32_t(p[17]) << 16) | (uint32_t(p[18]) << 8) | p[19];
    uint32_t height = (uint32_t(p[20]) << 24) | (uint32_t(p[21]) << 16) | (uint32_t(p[22]) << 8) | p[23];

    std::vector<uint8_t> ico;
    auto put16 = [&](uint16_t v) { ico.push_back(uint8_t(v & 0xFF)); ico.push_back(uint8_t(v >> 8)); };
    auto put32 = [&](uint32_t v) { put16(uint16_t(v & 0xFFFF)); put16(uint16_t(v >> 16)); };
    put16(0);  // reserved
    put16(1);  // type: icon
    put16(1);  // one image
    ico.push_back(width >= 256 ? 0 : uint8_t(width));
    ico.push_back(height >= 256 ? 0 : uint8_t(height));
    ico.push_back(0);  // palette colors
    ico.push_back(0);  // reserved
    put16(1);          // planes
    put16(32);         // bits per pixel
    put32(uint32_t(icon.size));
    put32(22);  // offset of the image data
    ico.insert(ico.end(), p, p + icon.size);

    wchar_t exe[MAX_PATH] = {0};
    DWORD n = GetModuleFileNameW(nullptr, exe, MAX_PATH);
    if (n == 0) {
      REXLOG_WARN("icon: cannot find the exe folder");
      return;
    }
    std::filesystem::path ico_path = std::filesystem::path(std::wstring(exe, n)).parent_path() / L"madden08.ico";
    {
      std::ofstream f(ico_path, std::ios::binary);
      if (f) {
        f.write(reinterpret_cast<const char*>(ico.data()), static_cast<std::streamsize>(ico.size()));
      }
      if (!f || !f.good()) {
        REXLOG_WARN("icon: cannot write {}", ico_path.string());
      }
    }
    HICON big = static_cast<HICON>(LoadImageW(nullptr, ico_path.c_str(), IMAGE_ICON,
                                              GetSystemMetrics(SM_CXICON), GetSystemMetrics(SM_CYICON),
                                              LR_LOADFROMFILE));
    HICON small_icon = static_cast<HICON>(LoadImageW(nullptr, ico_path.c_str(), IMAGE_ICON,
                                                     GetSystemMetrics(SM_CXSMICON), GetSystemMetrics(SM_CYSMICON),
                                                     LR_LOADFROMFILE));
    if (big) {
      SendMessageW(hwnd, WM_SETICON, ICON_BIG, reinterpret_cast<LPARAM>(big));
    }
    if (small_icon) {
      SendMessageW(hwnd, WM_SETICON, ICON_SMALL, reinterpret_cast<LPARAM>(small_icon));
    }
    REXLOG_INFO("icon: {}x{} title icon applied (big={}, small={}), saved to {}", width, height,
                big != nullptr, small_icon != nullptr, ico_path.string());
  }
#endif
};
