"""NBA 30 Teams Official Color Schemes & Presets."""

NBA_TEAMS = {
    "OKC": {
        "name": "Oklahoma City Thunder",
        "name_zh": "俄克拉荷马城雷霆队",
        "primary": (0, 125, 195),       # Thunder Blue
        "secondary": (239, 59, 36),     # Thunder Orange
        "accent": (255, 212, 92),       # Gold
        "dark": (15, 25, 38),
    },
    "DET": {
        "name": "Detroit Pistons",
        "name_zh": "底特律活塞队",
        "primary": (29, 66, 138),       # Royal Blue
        "secondary": (198, 12, 48),     # Crimson Red
        "accent": (255, 212, 92),
        "dark": (18, 20, 32),
    },
    "LAL": {
        "name": "Los Angeles Lakers",
        "name_zh": "洛杉矶湖人队",
        "primary": (85, 37, 130),       # Forum Blue / Purple
        "secondary": (253, 185, 39),    # Gold
        "accent": (255, 212, 92),
        "dark": (20, 15, 30),
    },
    "GSW": {
        "name": "Golden State Warriors",
        "name_zh": "金州勇士队",
        "primary": (29, 66, 138),       # Royal Blue
        "secondary": (255, 199, 44),    # California Golden
        "accent": (255, 212, 92),
        "dark": (14, 22, 36),
    },
    "BOS": {
        "name": "Boston Celtics",
        "name_zh": "波士顿凯尔特人队",
        "primary": (0, 122, 51),        # Celtic Green
        "secondary": (235, 186, 56),    # Gold
        "accent": (255, 212, 92),
        "dark": (10, 26, 18),
    },
    "MIA": {
        "name": "Miami Heat",
        "name_zh": "迈阿密热火队",
        "primary": (152, 0, 46),        # Maroon
        "secondary": (249, 160, 27),    # Heat Yellow
        "accent": (255, 212, 92),
        "dark": (28, 12, 18),
    },
    "CHI": {
        "name": "Chicago Bulls",
        "name_zh": "芝加哥公牛队",
        "primary": (206, 17, 65),       # Bulls Red
        "secondary": (6, 25, 34),       # Black
        "accent": (255, 212, 92),
        "dark": (20, 12, 16),
    },
    "HOU": {
        "name": "Houston Rockets",
        "name_zh": "休斯顿火箭队",
        "primary": (206, 17, 65),
        "secondary": (196, 206, 211),
        "accent": (255, 212, 92),
        "dark": (24, 14, 18),
    },
    "SAS": {
        "name": "San Antonio Spurs",
        "name_zh": "圣安东尼奥马刺队",
        "primary": (196, 206, 211),     # Silver
        "secondary": (0, 0, 0),         # Black
        "accent": (255, 212, 92),
        "dark": (18, 18, 22),
    },
    "DAL": {
        "name": "Dallas Mavericks",
        "name_zh": "达拉斯独行侠队",
        "primary": (0, 83, 188),        # Mavs Blue
        "secondary": (0, 43, 92),       # Navy
        "accent": (255, 212, 92),
        "dark": (12, 20, 36),
    },
    "DEN": {
        "name": "Denver Nuggets",
        "name_zh": "丹佛掘金队",
        "primary": (13, 34, 64),        # Midnight Blue
        "secondary": (254, 197, 36),    # Sunshine Gold
        "accent": (139, 35, 50),        # Flatirons Red
        "dark": (10, 18, 30),
    },
    "MIL": {
        "name": "Milwaukee Bucks",
        "name_zh": "密尔沃基雄鹿队",
        "primary": (0, 71, 27),         # Good Land Green
        "secondary": (238, 231, 207),   # Cream City Cream
        "accent": (255, 212, 92),
        "dark": (10, 24, 16),
    },
    "PHX": {
        "name": "Phoenix Suns",
        "name_zh": "菲尼克斯太阳队",
        "primary": (29, 17, 96),        # Purple
        "secondary": (229, 95, 32),     # Orange
        "accent": (255, 212, 92),
        "dark": (18, 14, 30),
    },
    "NYK": {
        "name": "New York Knicks",
        "name_zh": "纽约尼克斯队",
        "primary": (0, 107, 182),       # Blue
        "secondary": (245, 132, 38),    # Orange
        "accent": (255, 212, 92),
        "dark": (14, 24, 38),
    },
    "PHI": {
        "name": "Philadelphia 76ers",
        "name_zh": "费城76人队",
        "primary": (0, 107, 182),       # Blue
        "secondary": (237, 23, 76),     # Red
        "accent": (255, 212, 92),
        "dark": (14, 22, 36),
    },
}

def get_team_colors(team_key: str) -> dict:
    key = team_key.upper().strip()
    return NBA_TEAMS.get(key, NBA_TEAMS["OKC"])
