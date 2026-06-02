from textual.theme import Theme

# Cyberpunk palette:
#   #1B1B2A dark   #FF007A pink   #00FFB3 teal   #A700FF purple   #FFEA00 yellow
CYBERPUNK = Theme(
    name="cyberpunk",
    primary="#FF007A",
    secondary="#00FFB3",
    accent="#A700FF",
    warning="#FFEA00",
    error="#FF007A",
    success="#00FFB3",
    foreground="#E8E8F0",
    background="#1B1B2A",
    surface="#25253A",
    panel="#2D2D44",
    dark=True,
)

# Custom themes to register on startup. Add new Theme(...) objects here and they
# show up in the palette picker alongside Textual's built-in themes.
THEMES = [CYBERPUNK]
