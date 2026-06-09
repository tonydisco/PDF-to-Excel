use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::Manager;

// Giữ handle tiến trình sidecar Python để TẮT khi app thoát (tránh orphan).
struct Sidecar(Mutex<Option<Child>>);

fn spawn_sidecar() -> Option<Child> {
  // Dev: cwd của cargo run là desktop/src-tauri -> repo root = ../.. ; dùng venv.
  // Prod (đóng gói): sẽ thay bằng sidecar bundle (PyInstaller) ở bước sau.
  if cfg!(debug_assertions) {
    let cwd = std::env::current_dir().ok()?;
    let root = cwd.parent()?.parent()?.to_path_buf();
    let py = root.join(".venv/bin/python");
    let script = root.join("sidecar.py");
    match Command::new(&py).arg(&script).current_dir(&root).spawn() {
      Ok(child) => {
        println!("[sidecar] spawned: {} {}", py.display(), script.display());
        Some(child)
      }
      Err(e) => {
        eprintln!("[sidecar] spawn failed: {e}");
        None
      }
    }
  } else {
    None
  }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      app.manage(Sidecar(Mutex::new(spawn_sidecar())));
      Ok(())
    })
    .build(tauri::generate_context!())
    .expect("error while building tauri application")
    .run(|app, event| {
      if let tauri::RunEvent::Exit = event {
        if let Some(state) = app.try_state::<Sidecar>() {
          if let Some(mut child) = state.0.lock().unwrap().take() {
            let _ = child.kill();
          }
        }
      }
    });
}
