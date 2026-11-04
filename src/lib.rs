pub mod config;
pub mod error;
pub mod file;
pub mod service;
pub mod theme;
pub mod window;

pub use config::Config;
pub use error::ComponentError;
pub use file::FileManager;
pub use service::Service;
pub use theme::ThemeManager;
pub use window::WindowManager;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_file_manager_creation() {
        let fm = FileManager::default();
        let res = fm.list_directory();
        assert!(res.is_ok());
    }

    #[test]
    fn test_theme_manager() {
        let mut tm = ThemeManager::new();
        let theme = theme::Theme::new("TestTheme".to_string());
        tm.add_theme(theme);
        assert!(tm.set_current_theme("TestTheme").is_ok());
    }
}
