-- CHAROS — WezTerm TC Workspace
-- The TC terminal. The workshop entrance.
-- Opens with the CHAROS header, then TC launches and greets Dad.

local wezterm = require 'wezterm'
local config = wezterm.config_builder()

-- ── Colors — Ember on Charcoal ─────────────────────────────────────────────
config.colors = {
  foreground = '#e8e8e8',
  background = '#1a1a1a',
  cursor_bg = '#FF5900',
  cursor_border = '#FF5900',
  cursor_fg = '#1a1a1a',
  selection_bg = '#FF5900',
  selection_fg = '#1a1a1a',

  ansi = {
    '#1a1a1a',   -- black
    '#cc4444',   -- red
    '#66cc88',   -- green
    '#FF8C00',   -- yellow (ember light)
    '#5588cc',   -- blue
    '#8866cc',   -- magenta
    '#66cccc',   -- cyan
    '#e8e8e8',   -- white
  },
  brights = {
    '#333333',   -- bright black
    '#ff6666',   -- bright red
    '#88ffaa',   -- bright green
    '#FF5900',   -- bright yellow (full ember)
    '#88aaff',   -- bright blue
    '#aa88ff',   -- bright magenta
    '#88ffff',   -- bright cyan
    '#ffffff',   -- bright white
  },
}

-- ── Font ───────────────────────────────────────────────────────────────────
config.font = wezterm.font('JetBrains Mono', { weight = 'Regular' })
config.font_size = 13.0
config.line_height = 1.2

-- ── Window ─────────────────────────────────────────────────────────────────
config.window_background_opacity = 0.95
config.macos_window_background_blur = 20
config.window_padding = { left = 16, right = 16, top = 16, bottom = 16 }
config.enable_tab_bar = true
config.tab_bar_at_bottom = true
config.hide_tab_bar_if_only_one_tab = true
config.window_decorations = "RESIZE"

-- Tab styling
config.colors.tab_bar = {
  background = '#111111',
  active_tab = {
    bg_color = '#FF5900',
    fg_color = '#1a1a1a',
    intensity = 'Bold',
  },
  inactive_tab = {
    bg_color = '#1a1a1a',
    fg_color = '#555555',
  },
  inactive_tab_hover = {
    bg_color = '#222222',
    fg_color = '#FF5900',
  },
}

-- ── TC Launch Command ──────────────────────────────────────────────────────
-- Opens the tc-launch script which shows the CHAROS header,
-- then launches claude --dangerously-skip-permissions
-- TC's CLAUDE.md instructs him to greet Dad on every session start.
config.default_prog = { '/home/nathan/.charos/scripts/tc-launch.sh' }

-- ── Keybindings ────────────────────────────────────────────────────────────
config.keys = {
  -- New TC session
  { key = 't', mods = 'CTRL|SHIFT', action = wezterm.action.SpawnTab 'CurrentPaneDomain' },
  -- Split pane horizontal
  { key = 'h', mods = 'CTRL|SHIFT', action = wezterm.action.SplitHorizontal { domain = 'CurrentPaneDomain' } },
  -- Split pane vertical
  { key = 'v', mods = 'CTRL|SHIFT', action = wezterm.action.SplitVertical { domain = 'CurrentPaneDomain' } },
  -- Fullscreen
  { key = 'F11', mods = '', action = wezterm.action.ToggleFullScreen },
}

-- ── Title ──────────────────────────────────────────────────────────────────
wezterm.on('format-title', function(window, pane)
  return 'CHAROS // TC Nest'
end)

return config
