# ═══════════════════════════════════════════
#  Apple Design Language — 百度网盘文件管理器
#  基于 Apple DESIGN.md 令牌
# ═══════════════════════════════════════════

# ── 品牌色（来自 Apple DESIGN.md） ──
PRIMARY_COLOR = "#0066cc"        # Action Blue — 唯一的交互色
PRIMARY_HOVER = "#0071e3"        # Focus Blue — hover/focus 状态
PRIMARY_PRESSED = "#0055aa"      # 按下变深
PRIMARY_ON_DARK = "#2997ff"      # Sky Link Blue — 深色表面上的链接色

# ── 功能色 ──
SUCCESS_COLOR = "#34C759"        # Apple 风格绿色
DANGER_COLOR = "#FF3B30"         # Apple 风格红色
WARNING_COLOR = "#FF9500"        # Apple 风格橙色

# ── 表面色（Apple 表面层级） ──
CANVAS = "#ffffff"               # 纯白画布
CANVAS_PARCHMENT = "#f5f5f7"     # 米白 parchment — Apple 标志性底色
SURFACE_PEARL = "#fafafc"        # 珍珠白 — 次要按钮
SURFACE_BLACK = "#000000"        # 纯黑 — 仅导航栏

# ── 文字色（Apple ink 系统） ──
INK = "#1d1d1f"                  # 正文黑 — 不是纯黑，略带摄影质感
INK_MUTED_80 = "#333333"         # 次要文字
INK_MUTED_48 = "#7a7a7a"         # 提示/禁用文字

# ── 分隔线 ──
DIVIDER_SOFT = "#f0f0f0"         # 柔光分隔
HAIRLINE = "#e0e0e0"             # 1px 细线

# ── 交互 ──
HOVER_BG = "rgba(0, 0, 0, 0.04)"  # 悬停微光
SELECTED_BG = "#d6e4fd"           # 选中态（Apple 不常用强选中色）

# ── 字体（Apple 用 SF Pro，Windows 用 Segoe UI 近似） ──
FONT_FAMILY = (
    '"Segoe UI Variable", '
    '"Segoe UI", '
    '"SF Pro Text", '
    '"SF Pro Display", '
    'system-ui, '
    '-apple-system, '
    '"PingFang SC", '
    '"Microsoft YaHei UI", '
    'sans-serif'
)

# ── 圆角（Apple 圆角体系） ──
RADIUS_NONE = "0px"
RADIUS_XS = "5px"
RADIUS_SM = "8px"
RADIUS_MD = "11px"
RADIUS_LG = "18px"
RADIUS_PILL = "9999px"

# ── 阴影（Apple 仅对产品图使用阴影，UI 元素不用） ──
PRODUCT_SHADOW = "rgba(0, 0, 0, 0.22) 3px 5px 30px 0"


def get_stylesheet() -> str:
    return f"""
    /* ══════════════════════════════════════════
       Global — Apple Design System
       ══════════════════════════════════════════ */

    QWidget {{
        font-family: {FONT_FAMILY};
        font-size: 13px;
        color: {INK};
        background-color: {CANVAS_PARCHMENT};
    }}

    QMainWindow {{
        background-color: {CANVAS_PARCHMENT};
    }}

    /* ── 主按钮 — Apple 蓝色药丸 ── */
    QPushButton {{
        background-color: {PRIMARY_COLOR};
        color: white;
        border: none;
        border-radius: {RADIUS_PILL};
        padding: 8px 20px;
        font-size: 14px;
        font-weight: 500;
        letter-spacing: -0.2px;
    }}
    QPushButton:hover {{
        background-color: {PRIMARY_HOVER};
    }}
    QPushButton:pressed {{
        background-color: {PRIMARY_PRESSED};
    }}
    QPushButton:disabled {{
        background-color: {HAIRLINE};
        color: {INK_MUTED_48};
    }}

    /* 危险按钮 — Apple 红 */
    QPushButton#dangerBtn {{
        background-color: {DANGER_COLOR};
        border-radius: {RADIUS_PILL};
    }}
    QPushButton#dangerBtn:hover {{
        background-color: #E0352B;
    }}
    QPushButton#dangerBtn:pressed {{
        background-color: #C42D25;
    }}

    /* 次要按钮 — 幽灵按钮 */
    QPushButton#secondaryBtn {{
        background-color: {CANVAS};
        color: {PRIMARY_COLOR};
        border: 1px solid {HAIRLINE};
        border-radius: {RADIUS_PILL};
    }}
    QPushButton#secondaryBtn:hover {{
        background-color: {SURFACE_PEARL};
        border-color: {PRIMARY_COLOR};
    }}
    QPushButton#secondaryBtn:pressed {{
        background-color: {DIVIDER_SOFT};
    }}

    /* 小号按钮 */
    QPushButton#smallBtn {{
        background-color: {CANVAS};
        color: {INK_MUTED_80};
        border: 1px solid {DIVIDER_SOFT};
        padding: 4px 10px;
        font-size: 12px;
        border-radius: {RADIUS_SM};
        letter-spacing: -0.1px;
    }}
    QPushButton#smallBtn:hover {{
        background-color: {SURFACE_PEARL};
        border-color: {PRIMARY_COLOR};
        color: {PRIMARY_COLOR};
    }}

    /* ── 输入框 — Apple 搜索框风格 ── */
    QLineEdit {{
        background-color: {CANVAS};
        border: 1px solid {HAIRLINE};
        border-radius: {RADIUS_PILL};
        padding: 8px 16px;
        font-size: 14px;
        color: {INK};
        selection-background-color: {SELECTED_BG};
    }}
    QLineEdit:focus {{
        border-color: {PRIMARY_COLOR};
    }}
    QLineEdit::placeholder {{
        color: {INK_MUTED_48};
    }}

    /* ── 表格 — 整洁无影 ── */
    QTableView {{
        background-color: {CANVAS};
        alternate-background-color: {SURFACE_PEARL};
        border: 1px solid {DIVIDER_SOFT};
        border-radius: {RADIUS_LG};
        gridline-color: transparent;
        selection-background-color: {SELECTED_BG};
        selection-color: {INK};
        font-size: 14px;
        outline: none;
    }}
    QTableView::item {{
        padding: 8px 12px;
        min-height: 22px;
        border-bottom: 1px solid {DIVIDER_SOFT};
    }}
    QTableView::item:hover {{
        background-color: #F5F5F7;
    }}
    QTableView::item:selected {{
        background-color: {SELECTED_BG};
    }}
    QHeaderView::section {{
        background-color: {SURFACE_PEARL};
        color: {INK_MUTED_80};
        font-weight: 600;
        font-size: 12px;
        letter-spacing: -0.12px;
        border: none;
        border-bottom: 1px solid {HAIRLINE};
        padding: 10px 12px;
    }}
    QHeaderView::section:hover {{
        color: {PRIMARY_COLOR};
        background-color: {DIVIDER_SOFT};
    }}

    /* ── 目录树 — 侧栏干净 ── */
    QTreeView {{
        background-color: {CANVAS};
        border: 1px solid {DIVIDER_SOFT};
        border-radius: {RADIUS_LG};
        font-size: 14px;
        outline: none;
    }}
    QTreeView::item {{
        padding: 7px 10px;
        min-height: 20px;
        border-radius: {RADIUS_SM};
        margin: 1px 4px;
        color: {INK};
    }}
    QTreeView::item:hover {{
        background-color: #F5F5F7;
    }}
    QTreeView::item:selected {{
        background-color: {SELECTED_BG};
        color: {INK};
    }}
    QTreeView::branch {{
        background-color: transparent;
    }}

    /* ── 标签页 — Apple 风格 ── */
    QTabWidget::pane {{
        border: none;
        background-color: {CANVAS_PARCHMENT};
        top: -1px;
    }}
    QTabBar::tab {{
        background-color: transparent;
        color: {INK_MUTED_80};
        border: none;
        border-radius: {RADIUS_SM} {RADIUS_SM} 0 0;
        padding: 7px 18px;
        margin-right: 2px;
        margin-top: 4px;
        font-size: 13px;
        font-weight: 500;
        min-width: 80px;
        max-width: 180px;
    }}
    QTabBar::tab:hover {{
        background-color: {DIVIDER_SOFT};
        color: {INK};
    }}
    QTabBar::tab:selected {{
        background-color: {CANVAS};
        color: {PRIMARY_COLOR};
        font-weight: 600;
    }}

    /* ── 滚动条 — 极简 ── */
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {HAIRLINE};
        border-radius: 3px;
        min-height: 36px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {INK_MUTED_48};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 6px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {HAIRLINE};
        border-radius: 3px;
        min-width: 36px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {INK_MUTED_48};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    /* ── 复选框 ── */
    QCheckBox {{
        spacing: 6px;
        font-size: 14px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1.5px solid {HAIRLINE};
        border-radius: {RADIUS_XS};
        background-color: {CANVAS};
    }}
    QCheckBox::indicator:checked {{
        background-color: {PRIMARY_COLOR};
        border-color: {PRIMARY_COLOR};
    }}

    /* ── 进度条 ── */
    QProgressBar {{
        background-color: {DIVIDER_SOFT};
        border: none;
        border-radius: 4px;
        text-align: center;
        font-size: 12px;
        color: {INK_MUTED_80};
        height: 6px;
    }}
    QProgressBar::chunk {{
        background-color: {PRIMARY_COLOR};
        border-radius: 4px;
    }}

    /* ── 对话框 ── */
    QDialog {{
        background-color: {CANVAS_PARCHMENT};
        border-radius: {RADIUS_LG};
    }}

    /* ── 标签 ── */
    QLabel {{
        color: {INK};
        background: transparent;
    }}
    QLabel#hintLabel {{
        color: {INK_MUTED_48};
        font-size: 12px;
    }}
    QLabel#titleLabel {{
        font-size: 21px;
        font-weight: 600;
        color: {INK};
        letter-spacing: -0.2px;
    }}
    QLabel#subtitleLabel {{
        font-size: 14px;
        font-weight: 600;
        color: {INK_MUTED_80};
    }}

    /* ── 分割线 — 无装饰，仅颜色变化 ── */
    QSplitter::handle {{
        background-color: transparent;
    }}
    QSplitter::handle:horizontal {{
        width: 1px;
    }}
    QSplitter::handle:vertical {{
        height: 1px;
    }}

    /* ── 工具栏 — 极简 ── */
    QFrame#toolbar {{
        background-color: {CANVAS};
        border-top: 1px solid {DIVIDER_SOFT};
    }}

    /* ── 导航栏 ── */
    QFrame#navBar {{
        background-color: {CANVAS};
        border-bottom: 1px solid {DIVIDER_SOFT};
    }}

    /* ── 状态栏 ── */
    QStatusBar {{
        background-color: {CANVAS};
        border-top: 1px solid {DIVIDER_SOFT};
        color: {INK_MUTED_80};
        font-size: 12px;
        letter-spacing: -0.1px;
    }}

    /* ── 菜单 — 无阴影，干净 ── */
    QMenu {{
        background-color: {CANVAS};
        border: 1px solid {HAIRLINE};
        border-radius: {RADIUS_SM};
        padding: 4px 0;
    }}
    QMenu::item {{
        padding: 7px 32px 7px 16px;
        border-radius: {RADIUS_XS};
        margin: 2px 4px;
        font-size: 14px;
    }}
    QMenu::item:selected {{
        background-color: #F5F5F7;
        color: {PRIMARY_COLOR};
    }}
    QMenu::separator {{
        height: 1px;
        background-color: {DIVIDER_SOFT};
        margin: 4px 8px;
    }}

    /* ── 下拉框 ── */
    QComboBox {{
        background-color: {CANVAS};
        border: 1px solid {HAIRLINE};
        border-radius: {RADIUS_PILL};
        padding: 7px 14px;
        font-size: 14px;
        color: {INK};
    }}
    QComboBox:hover {{
        border-color: {PRIMARY_COLOR};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {CANVAS};
        border: 1px solid {HAIRLINE};
        border-radius: {RADIUS_SM};
        selection-background-color: #F5F5F7;
        outline: none;
    }}

    /* ── 文本编辑 ── */
    QTextEdit, QPlainTextEdit {{
        background-color: {CANVAS};
        border: 1px solid {HAIRLINE};
        border-radius: {RADIUS_SM};
        padding: 8px;
        font-size: 14px;
        color: {INK};
    }}

    /* ── 搜索栏 ── */
    QFrame#searchBar {{
        background-color: {CANVAS_PARCHMENT};
        border-bottom: 1px solid {DIVIDER_SOFT};
        padding: 10px 14px;
    }}

    /* ── 标签栏操作按钮（+、分屏） ── */
    QPushButton#tabBtn {{
        background-color: transparent;
        color: {INK_MUTED_48};
        border: none;
        padding: 4px 8px;
        font-size: 18px;
        border-radius: {RADIUS_SM};
    }}
    QPushButton#tabBtn:hover {{
        background-color: {DIVIDER_SOFT};
        color: {PRIMARY_COLOR};
    }}

    /* ── 密码可见切换 ── */
    QPushButton#eyeBtn {{
        background-color: transparent;
        color: {INK_MUTED_48};
        border: none;
        padding: 4px;
        font-size: 16px;
        min-width: 28px;
        max-width: 28px;
    }}
    QPushButton#eyeBtn:hover {{
        color: {INK};
    }}
    """