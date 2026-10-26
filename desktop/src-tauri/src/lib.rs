pub mod api;
pub mod commands;
pub mod maps;
pub mod preview;
pub mod qr;
pub mod route;
pub mod settings;
pub mod stats;
pub mod task;
pub mod update;

pub use api::{LoginChallenge, LoginResult, Session};

/// 启动桌面应用。业务模块保持独立；`commands` 只做界面与 Rust 业务层之间的适配。
pub fn run() {
    commands::run();
}
