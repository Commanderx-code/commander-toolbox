use crate::{float::FloatContent, hint::Shortcut, shortcuts, theme};
use ratatui::{
    crossterm::event::{KeyCode, KeyEvent, MouseEvent, MouseEventKind},
    layout::Alignment,
    prelude::*,
    symbols::border,
    widgets::{Block, Clear, List, Paragraph},
};
use std::borrow::Cow;

pub enum ConfirmStatus {
    Confirm,
    Abort,
    None,
}

pub struct ConfirmPrompt {
    inner_area_height: usize,
    names: Box<[String]>,
    scroll: usize,
    pub status: ConfirmStatus,
}

impl ConfirmPrompt {
    pub fn new(names: &[&str]) -> Self {
        let max_count_str = format!("{}", names.len());
        let names = names
            .iter()
            .zip(1..)
            .map(|(name, n)| {
                let count_str = format!("{n}");
                let space_str = (0..(max_count_str.len() - count_str.len()))
                    .map(|_| ' ')
                    .collect::<String>();
                format!("{space_str}{n}. {name}")
            })
            .collect();

        Self {
            inner_area_height: 0,
            names,
            scroll: 0,
            status: ConfirmStatus::None,
        }
    }

    pub fn scroll_down(&mut self) {
        if self.scroll + self.inner_area_height < self.names.len() {
            self.scroll += 1;
        }
    }

    pub fn scroll_up(&mut self) {
        if self.scroll > 0 {
            self.scroll -= 1;
        }
    }
}

impl FloatContent for ConfirmPrompt {
    fn draw(&mut self, frame: &mut Frame, area: Rect, theme: &theme::Theme) {
        let block = Block::bordered()
            .border_set(border::PLAIN)
            .border_style(Style::default().fg(theme.focused_color()))
            .title(" CONFIRM SELECTIONS ")
            .title_alignment(Alignment::Center)
            .title_style(Style::default().fg(theme.tab_color()).bold())
            .style(Style::default());

        let inner_area = block.inner(area);
        let sections = Layout::vertical([
            Constraint::Min(1),
            Constraint::Length(1),
            Constraint::Length(2),
        ])
        .split(inner_area);
        self.inner_area_height = sections[0].height as usize;

        frame.render_widget(Clear, area);
        frame.render_widget(block, area);

        let paths_text = self
            .names
            .iter()
            .skip(self.scroll)
            .map(|p| {
                let span = Span::from(Cow::<'_, str>::Borrowed(p));
                Line::from(span).style(Style::default())
            })
            .collect::<Text>();

        frame.render_widget(List::new(paths_text), sections[0]);
        let actions = Text::from(vec![
            Line::styled(
                "[Y] Run / Install",
                Style::default().fg(theme.success_color()).bold(),
            ),
            Line::styled("[N] Cancel", Style::default().fg(theme.fail_color()).bold()),
        ]);
        frame.render_widget(
            Paragraph::new(actions).alignment(Alignment::Center),
            sections[2],
        );
    }

    fn handle_mouse_event(&mut self, event: &MouseEvent) -> bool {
        match event.kind {
            MouseEventKind::ScrollDown => {
                self.scroll_down();
            }
            MouseEventKind::ScrollUp => {
                self.scroll_up();
            }
            _ => {}
        }
        false
    }

    fn handle_key_event(&mut self, key: &KeyEvent) -> bool {
        use ConfirmStatus::*;
        use KeyCode::{Char, Down, Esc, Up};
        self.status = match key.code {
            Char('y') | Char('Y') => Confirm,
            Char('n') | Char('N') | Esc | Char('q') => Abort,
            Char('j') | Char('J') | Down => {
                self.scroll_down();
                None
            }
            Char('k') | Char('K') | Up => {
                self.scroll_up();
                None
            }
            _ => None,
        };
        false
    }

    fn is_finished(&self) -> bool {
        use ConfirmStatus::*;
        match self.status {
            Confirm | Abort => true,
            None => false,
        }
    }

    fn get_shortcut_list(&self) -> (&str, Box<[Shortcut]>) {
        (
            "Confirmation prompt",
            shortcuts!(
                ("Run / Install", ["Y", "y"]),
                ("Abort", ["N", "n", "q", "Esc"]),
                ("Scroll up", ["k", "Up"]),
                ("Scroll down", ["j", "Down"]),
                ("Close toolbox", ["CTRL-c"]),
            ),
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::{backend::TestBackend, crossterm::event::KeyModifiers, Terminal};

    #[test]
    fn install_and_cancel_are_visible_in_a_narrow_popup() {
        let mut prompt = ConfirmPrompt::new(&["Alacritty"]);
        let mut terminal = Terminal::new(TestBackend::new(24, 8)).unwrap();
        terminal
            .draw(|frame| prompt.draw(frame, frame.area(), &theme::Theme::Default))
            .unwrap();
        let buffer = terminal.backend().buffer();
        let text = (0..8)
            .map(|y| (0..24).map(|x| buffer[(x, y)].symbol()).collect::<String>())
            .collect::<Vec<_>>()
            .join("\n");
        assert!(text.contains("1. Alacritty"));
        assert!(text.contains("[Y] Run / Install"));
        assert!(text.contains("[N] Cancel"));
    }

    #[test]
    fn confirmation_still_requires_an_explicit_choice() {
        let mut prompt = ConfirmPrompt::new(&["Alacritty"]);
        prompt.handle_key_event(&KeyEvent::new(KeyCode::Enter, KeyModifiers::NONE));
        assert!(matches!(prompt.status, ConfirmStatus::None));
        prompt.handle_key_event(&KeyEvent::new(KeyCode::Char('y'), KeyModifiers::NONE));
        assert!(matches!(prompt.status, ConfirmStatus::Confirm));
        for code in [KeyCode::Char('n'), KeyCode::Esc] {
            prompt.handle_key_event(&KeyEvent::new(code, KeyModifiers::NONE));
            assert!(matches!(prompt.status, ConfirmStatus::Abort));
        }
    }

    #[test]
    fn scrolling_can_reach_the_last_selected_command() {
        let mut prompt = ConfirmPrompt::new(&["one", "two", "three"]);
        prompt.inner_area_height = 1;
        prompt.scroll_down();
        prompt.scroll_down();
        assert_eq!(prompt.scroll, 2);
        prompt.scroll_down();
        assert_eq!(prompt.scroll, 2);
    }
}
