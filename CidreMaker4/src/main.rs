#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use eframe::egui;
use std::path::PathBuf;

const BG: egui::Color32 = egui::Color32::from_rgb(17, 21, 27);
const PANEL: egui::Color32 = egui::Color32::from_rgb(25, 31, 39);
const CARD: egui::Color32 = egui::Color32::from_rgb(31, 39, 49);
const CARD_ALT: egui::Color32 = egui::Color32::from_rgb(36, 45, 56);
const TEXT: egui::Color32 = egui::Color32::from_rgb(229, 235, 240);
const MUTED: egui::Color32 = egui::Color32::from_rgb(143, 157, 171);
const ACCENT: egui::Color32 = egui::Color32::from_rgb(193, 157, 94);
const GREEN: egui::Color32 = egui::Color32::from_rgb(105, 176, 139);
const BLUE: egui::Color32 = egui::Color32::from_rgb(104, 157, 202);
const ORANGE: egui::Color32 = egui::Color32::from_rgb(211, 151, 87);

fn main() -> eframe::Result<()> {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title("CidreMaker 4")
            .with_inner_size([1440.0, 900.0])
            .with_min_inner_size([1100.0, 700.0]),
        ..Default::default()
    };

    eframe::run_native(
        "CidreMaker 4",
        options,
        Box::new(|cc| Ok(Box::new(CidreMakerApp::new(cc)))),
    )
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Page {
    Dashboard,
    Batches,
    Fermentation,
    Operations,
    Calculators,
    Library,
    Analytics,
    Settings,
}

impl Page {
    fn title(self) -> &'static str {
        match self {
            Self::Dashboard => "Обзор производства",
            Self::Batches => "Производственные партии",
            Self::Fermentation => "Брожение",
            Self::Operations => "Технологические операции",
            Self::Calculators => "Калькуляторы",
            Self::Library => "Справочники",
            Self::Analytics => "Аналитика",
            Self::Settings => "Настройки и данные",
        }
    }

    fn subtitle(self) -> &'static str {
        match self {
            Self::Dashboard => "Состояние производства и ближайшие задачи",
            Self::Batches => "История и управление всеми партиями",
            Self::Fermentation => "Измерения, динамика плотности и температура",
            Self::Operations => "Полная история технологических действий",
            Self::Calculators => "Расчёты с исходными данными и пояснениями",
            Self::Library => "Материалы, оборудование и технологические справочники",
            Self::Analytics => "Сравнение партий и производственные показатели",
            Self::Settings => "Portable-хранилище, резервные копии и перенос данных",
        }
    }
}

#[derive(Clone)]
struct Batch {
    code: String,
    name: String,
    kind: String,
    stage: String,
    volume: String,
    status: String,
    progress: f32,
}

struct CidreMakerApp {
    page: Page,
    batches: Vec<Batch>,
    selected_batch: usize,
    show_new_batch: bool,
    new_batch_name: String,
    new_batch_volume: String,
    search: String,
    data_dir: PathBuf,
}

impl CidreMakerApp {
    fn new(cc: &eframe::CreationContext<'_>) -> Self {
        configure_style(&cc.egui_ctx);
        let data_dir = portable_data_dir();

        Self {
            page: Page::Dashboard,
            batches: vec![
                Batch {
                    code: "CM-26-001".into(),
                    name: "Антоновка — моносорт".into(),
                    kind: "Игристый · Classic".into(),
                    stage: "Вторичное брожение".into(),
                    volume: "42 л".into(),
                    status: "Активна".into(),
                    progress: 0.72,
                },
                Batch {
                    code: "CM-26-002".into(),
                    name: "Осенний купаж".into(),
                    kind: "Тихий сидр".into(),
                    stage: "Выдержка".into(),
                    volume: "28 л".into(),
                    status: "Выдержка".into(),
                    progress: 0.88,
                },
                Batch {
                    code: "CM-26-003".into(),
                    name: "Грушевый Perry".into(),
                    kind: "Игристый · Pet-Nat".into(),
                    stage: "Первичное брожение".into(),
                    volume: "18 л".into(),
                    status: "Активна".into(),
                    progress: 0.36,
                },
                Batch {
                    code: "CM-26-004".into(),
                    name: "Яблоко + айва".into(),
                    kind: "Тихий сидр".into(),
                    stage: "Подготовка сырья".into(),
                    volume: "35 л".into(),
                    status: "Подготовка".into(),
                    progress: 0.12,
                },
            ],
            selected_batch: 0,
            show_new_batch: false,
            new_batch_name: String::new(),
            new_batch_volume: "20".into(),
            search: String::new(),
            data_dir,
        }
    }

    fn sidebar(&mut self, ctx: &egui::Context) {
        egui::SidePanel::left("navigation")
            .exact_width(238.0)
            .frame(egui::Frame::new().fill(PANEL).inner_margin(egui::Margin::same(14)))
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    ui.label(egui::RichText::new("CM").size(22.0).strong().color(ACCENT));
                    ui.vertical(|ui| {
                        ui.label(egui::RichText::new("CidreMaker").size(17.0).strong().color(TEXT));
                        ui.label(egui::RichText::new("STUDIO  ·  4.0").size(9.0).color(MUTED));
                    });
                });
                ui.add_space(28.0);
                ui.label(egui::RichText::new("РАБОЧЕЕ ПРОСТРАНСТВО").size(9.0).strong().color(MUTED));
                ui.add_space(8.0);

                self.nav_button(ui, Page::Dashboard, "⌂", "Обзор");
                self.nav_button(ui, Page::Batches, "▦", "Партии");
                self.nav_button(ui, Page::Fermentation, "◉", "Брожение");
                self.nav_button(ui, Page::Operations, "⇄", "Операции");

                ui.add_space(20.0);
                ui.label(egui::RichText::new("ИНСТРУМЕНТЫ").size(9.0).strong().color(MUTED));
                ui.add_space(8.0);
                self.nav_button(ui, Page::Calculators, "∑", "Калькуляторы");
                self.nav_button(ui, Page::Library, "▤", "Справочники");
                self.nav_button(ui, Page::Analytics, "⌁", "Аналитика");

                ui.add_space(20.0);
                ui.label(egui::RichText::new("СИСТЕМА").size(9.0).strong().color(MUTED));
                ui.add_space(8.0);
                self.nav_button(ui, Page::Settings, "⚙", "Настройки и данные");

                ui.with_layout(egui::Layout::bottom_up(egui::Align::Min), |ui| {
                    ui.add_space(10.0);
                    ui.label(egui::RichText::new("PORTABLE MODE").size(9.0).strong().color(GREEN));
                    ui.label(egui::RichText::new("Данные рядом с приложением").size(10.0).color(MUTED));
                    ui.separator();
                    ui.label(egui::RichText::new("CidreMaker 4 · Prototype").size(10.0).color(MUTED));
                });
            });
    }

    fn nav_button(&mut self, ui: &mut egui::Ui, page: Page, icon: &str, label: &str) {
        let active = self.page == page;
        let fill = if active { CARD_ALT } else { PANEL };
        let color = if active { ACCENT } else { MUTED };
        let response = egui::Frame::new()
            .fill(fill)
            .corner_radius(egui::CornerRadius::same(8))
            .inner_margin(egui::Margin::symmetric(10, 9))
            .show(ui, |ui| {
                ui.set_width(ui.available_width());
                ui.horizontal(|ui| {
                    ui.label(egui::RichText::new(icon).size(17.0).color(color));
                    ui.label(
                        egui::RichText::new(label)
                            .size(13.0)
                            .color(if active { TEXT } else { MUTED })
                            .strong(active),
                    );
                });
            })
            .response
            .interact(egui::Sense::click());
        if response.clicked() {
            self.page = page;
        }
        ui.add_space(3.0);
    }

    fn top_bar(&mut self, ctx: &egui::Context) {
        egui::TopBottomPanel::top("topbar")
            .frame(egui::Frame::new().fill(BG).inner_margin(egui::Margin::symmetric(22, 14)))
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    ui.vertical(|ui| {
                        ui.label(egui::RichText::new(self.page.title()).size(20.0).strong().color(TEXT));
                        ui.label(egui::RichText::new(self.page.subtitle()).size(11.0).color(MUTED));
                    });
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        let _ = ui.button("●  Профиль");
                        if ui.button("＋  Новая партия").clicked() {
                            self.show_new_batch = true;
                            self.page = Page::Batches;
                        }
                        ui.add_space(12.0);
                        ui.label(egui::RichText::new("16 ноября 2026").size(11.0).color(MUTED));
                    });
                });
            });
    }

    fn dashboard(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            ui.label(egui::RichText::new("Производство").size(16.0).strong().color(TEXT));
            ui.add_space(6.0);
            ui.label(egui::RichText::new(" /  Сводка по активным партиям").size(11.0).color(MUTED));
        });
        ui.add_space(14.0);

        ui.columns(4, |columns| {
            metric_card(&mut columns[0], "АКТИВНЫЕ ПАРТИИ", &self.batches.len().to_string(), "В работе", GREEN);
            metric_card(&mut columns[1], "ОБЩИЙ ОБЪЁМ", "123 л", "Во всех партиях", BLUE);
            metric_card(&mut columns[2], "НА БРОЖЕНИИ", "2", "Требуют контроля", ORANGE);
            metric_card(&mut columns[3], "БЛИЖАЙШИЕ ЗАДАЧИ", "3", "На этой неделе", ACCENT);
        });

        ui.add_space(18.0);
        ui.columns(2, |columns| {
            section_card(&mut columns[0], "Активные партии", "Открыть журнал") ;
            for batch in self.batches.iter().take(3) {
                batch_row(&mut columns[0], batch);
            }
            columns[0].add_space(8.0);
            if columns[0].button("Все партии →").clicked() {
                self.page = Page::Batches;
            }

            section_card(&mut columns[1], "Требуют внимания", "Контроль процесса");
            attention_row(&mut columns[1], "CM-26-001", "Проверить давление в бутылках", "Сегодня", ORANGE);
            attention_row(&mut columns[1], "CM-26-003", "Внести очередное измерение Brix", "Сегодня", BLUE);
            attention_row(&mut columns[1], "CM-26-004", "Запланировать внесение дрожжей", "Завтра", GREEN);
        });

        ui.add_space(18.0);
        ui.columns(2, |columns| {
            columns[0].vertical(|ui| {
                section_card(ui, "Производственный цикл", "Этапы партии");
                ui.horizontal_wrapped(|ui| {
                    for (name, count) in [("Подготовка", "1"), ("Брожение", "1"), ("Выдержка", "1"), ("Розлив", "1")] {
                        egui::Frame::new().fill(CARD).corner_radius(8).inner_margin(10.0).show(ui, |ui| {
                            ui.label(egui::RichText::new(count).size(20.0).strong().color(ACCENT));
                            ui.label(egui::RichText::new(name).size(10.0).color(MUTED));
                        });
                    }
                });
            });
            columns[1].vertical(|ui| {
                section_card(ui, "Динамика брожения", "Демонстрационный график");
                draw_demo_chart(ui);
            });
        });
    }

    fn batches_page(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            ui.label(egui::RichText::new("Журнал партий").size(15.0).strong().color(TEXT));
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                if ui.button("＋ Создать партию").clicked() {
                    self.show_new_batch = true;
                }
                ui.add_space(8.0);
                ui.add(egui::TextEdit::singleline(&mut self.search).hint_text("Поиск по названию или коду…").desired_width(230.0));
            });
        });
        ui.add_space(12.0);

        egui::Grid::new("batches_table")
            .num_columns(6)
            .striped(true)
            .spacing([16.0, 12.0])
            .show(ui, |ui| {
                for heading in ["КОД", "НАЗВАНИЕ", "ТИП", "ЭТАП", "ОБЪЁМ", "СТАТУС"] {
                    ui.label(egui::RichText::new(heading).size(9.0).strong().color(MUTED));
                }
                ui.end_row();

                let needle = self.search.to_lowercase();
                for (index, batch) in self.batches.iter().enumerate() {
                    if !needle.is_empty()
                        && !batch.name.to_lowercase().contains(&needle)
                        && !batch.code.to_lowercase().contains(&needle)
                    {
                        continue;
                    }
                    let selected = self.selected_batch == index;
                    let response = ui.selectable_label(selected, egui::RichText::new(&batch.code).color(ACCENT));
                    if response.clicked() {
                        self.selected_batch = index;
                    }
                    ui.label(egui::RichText::new(&batch.name).color(TEXT));
                    ui.label(egui::RichText::new(&batch.kind).color(MUTED));
                    ui.label(egui::RichText::new(&batch.stage).color(TEXT));
                    ui.label(egui::RichText::new(&batch.volume).color(TEXT));
                    ui.label(egui::RichText::new(&batch.status).color(GREEN));
                    ui.end_row();
                }
            });

        if let Some(batch) = self.batches.get(self.selected_batch) {
            ui.add_space(22.0);
            egui::Frame::new().fill(CARD).corner_radius(10).inner_margin(16.0).show(ui, |ui| {
                ui.label(egui::RichText::new("Выбранная партия").size(12.0).strong().color(ACCENT));
                ui.add_space(5.0);
                ui.heading(egui::RichText::new(&batch.name).color(TEXT));
                ui.label(egui::RichText::new(format!("{}  ·  {}  ·  {}", batch.code, batch.kind, batch.stage)).color(MUTED));
                ui.add_space(8.0);
                ui.add(egui::ProgressBar::new(batch.progress).text(format!("Готовность этапа: {:.0}%", batch.progress * 100.0)));
            });
        }
    }

    fn placeholder_page(&self, ui: &mut egui::Ui) {
        let (headline, description, items) = match self.page {
            Page::Fermentation => ("Журнал брожения", "Все измерения будут привязаны к конкретной партии и времени.", vec!["Brix / SG / Plato", "Температура и динамика", "Подкормки и добавки", "График изменения плотности"]),
            Page::Operations => ("История технологических операций", "Операции формируют прослеживаемую историю каждой партии.", vec!["Прессование и подготовка сусла", "Переливы и снятие с осадка", "Купажирование и выдержка", "Розлив, тираж и дегоржаж"]),
            Page::Calculators => ("Расчётный центр", "Каждый расчёт будет показывать формулу, исходные данные, единицы и предупреждения.", vec!["Крепость и коррекция рефрактометра", "Карбонизация и остаточный сахар", "Тиражный и экспедиционный ликёры", "Pet-Nat, купажирование и Solera"]),
            Page::Library => ("Технологические справочники", "Пользовательские записи и локальные справочники будут храниться в portable-проекте.", vec!["Дрожжи и бактерии", "Питательные вещества и ферменты", "Осветлители и стабилизаторы", "Бутылки, давление и укупорка"]),
            Page::Analytics => ("Аналитика производства", "Сравнение партий, истории измерений и сенсорных оценок.", vec!["Динамика брожения", "Сравнение партий и урожаев", "Выход сока и потери", "История дегустаций"]),
            Page::Settings => ("Portable-хранилище", "Данные не должны зависеть от профиля Windows или установки программы.", vec!["База данных SQLite рядом с EXE", "Фото и вложения в отдельной папке", "Резервные копии и восстановление", "Импорт и экспорт проектов"]),
            _ => ("Раздел", "Выберите раздел в боковом меню.", vec![]),
        };

        egui::Frame::new().fill(CARD).corner_radius(12).inner_margin(22.0).show(ui, |ui| {
            ui.label(egui::RichText::new("СЛЕДУЮЩИЙ ЭТАП РАЗРАБОТКИ").size(9.0).strong().color(ACCENT));
            ui.add_space(8.0);
            ui.heading(egui::RichText::new(headline).color(TEXT));
            ui.label(egui::RichText::new(description).color(MUTED));
            ui.add_space(18.0);
            for item in items {
                ui.horizontal(|ui| {
                    ui.label(egui::RichText::new("◆").color(ACCENT));
                    ui.label(egui::RichText::new(item).color(TEXT));
                });
                ui.add_space(8.0);
            }
            ui.add_space(10.0);
            ui.label(egui::RichText::new("Этот экран — каркас интерфейса. Функциональность будет подключаться поэтапно.").size(11.0).color(MUTED));
        });
    }

    fn new_batch_dialog(&mut self, ctx: &egui::Context) {
        if !self.show_new_batch {
            return;
        }
        egui::Window::new("Новая производственная партия")
            .collapsible(false)
            .resizable(false)
            .anchor(egui::Align2::CENTER_CENTER, [0.0, 0.0])
            .show(ctx, |ui| {
                ui.set_width(360.0);
                ui.label("Название партии");
                ui.add(egui::TextEdit::singleline(&mut self.new_batch_name).hint_text("Например, Антоновка 2027"));
                ui.add_space(8.0);
                ui.label("Начальный объём, литры");
                ui.add(egui::TextEdit::singleline(&mut self.new_batch_volume));
                ui.add_space(14.0);
                ui.horizontal(|ui| {
                    if ui.button("Создать").clicked() {
                        let name = self.new_batch_name.trim();
                        let volume = self.new_batch_volume.trim().parse::<f32>().unwrap_or(0.0);
                        if !name.is_empty() && volume > 0.0 {
                            let code = format!("CM-26-{:03}", self.batches.len() + 1);
                            self.batches.push(Batch {
                                code,
                                name: name.to_owned(),
                                kind: "Не указан".into(),
                                stage: "Подготовка сырья".into(),
                                volume: format!("{volume:.1} л"),
                                status: "Подготовка".into(),
                                progress: 0.02,
                            });
                            self.selected_batch = self.batches.len() - 1;
                            self.new_batch_name.clear();
                            self.show_new_batch = false;
                        }
                    }
                    if ui.button("Отмена").clicked() {
                        self.show_new_batch = false;
                    }
                });
            });
    }
}

impl eframe::App for CidreMakerApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.sidebar(ctx);
        self.top_bar(ctx);

        egui::CentralPanel::default()
            .frame(egui::Frame::new().fill(BG).inner_margin(egui::Margin::same(22)))
            .show(ctx, |ui| {
                egui::ScrollArea::vertical().show(ui, |ui| {
                    match self.page {
                        Page::Dashboard => self.dashboard(ui),
                        Page::Batches => self.batches_page(ui),
                        _ => self.placeholder_page(ui),
                    }
                });
            });

        egui::TopBottomPanel::bottom("statusbar")
            .frame(egui::Frame::new().fill(PANEL).inner_margin(egui::Margin::symmetric(14, 6)))
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    ui.label(egui::RichText::new("●").color(GREEN));
                    ui.label(egui::RichText::new("Локальный режим").size(10.0).color(MUTED));
                    ui.separator();
                    ui.label(egui::RichText::new(format!("Хранилище: {}", self.data_dir.display())).size(10.0).color(MUTED));
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        ui.label(egui::RichText::new("Демонстрационные данные · не сохраняются").size(10.0).color(ORANGE));
                    });
                });
            });

        self.new_batch_dialog(ctx);
    }
}

fn configure_style(ctx: &egui::Context) {
    let mut style = (*ctx.style()).clone();
    style.visuals = egui::Visuals::dark();
    style.visuals.panel_fill = BG;
    style.visuals.window_fill = PANEL;
    style.visuals.extreme_bg_color = egui::Color32::from_rgb(13, 17, 22);
    style.visuals.widgets.inactive.bg_fill = CARD;
    style.visuals.widgets.hovered.bg_fill = CARD_ALT;
    style.visuals.widgets.active.bg_fill = ACCENT;
    style.visuals.selection.bg_fill = egui::Color32::from_rgb(83, 71, 52);
    style.spacing.item_spacing = egui::vec2(8.0, 8.0);
    ctx.set_style(style);
}

fn portable_data_dir() -> PathBuf {
    let base = std::env::current_exe()
        .ok()
        .and_then(|path| path.parent().map(PathBuf::from))
        .or_else(|| std::env::current_dir().ok())
        .unwrap_or_else(|| PathBuf::from("."));
    let dir = base.join("CidreMakerData");
    let _ = std::fs::create_dir_all(&dir);
    dir
}

fn metric_card(ui: &mut egui::Ui, title: &str, value: &str, note: &str, accent: egui::Color32) {
    egui::Frame::new().fill(CARD).corner_radius(10).inner_margin(14.0).show(ui, |ui| {
        ui.set_min_height(94.0);
        ui.label(egui::RichText::new(title).size(9.0).strong().color(MUTED));
        ui.add_space(7.0);
        ui.label(egui::RichText::new(value).size(27.0).strong().color(accent));
        ui.label(egui::RichText::new(note).size(10.0).color(MUTED));
    });
}

fn section_card(ui: &mut egui::Ui, title: &str, note: &str) {
    ui.horizontal(|ui| {
        ui.label(egui::RichText::new(title).size(13.0).strong().color(TEXT));
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            ui.label(egui::RichText::new(note).size(9.0).color(MUTED));
        });
    });
    ui.add_space(9.0);
}

fn batch_row(ui: &mut egui::Ui, batch: &Batch) {
    egui::Frame::new().fill(CARD).corner_radius(8).inner_margin(10.0).show(ui, |ui| {
        ui.horizontal(|ui| {
            ui.vertical(|ui| {
                ui.label(egui::RichText::new(&batch.name).size(11.0).strong().color(TEXT));
                ui.label(egui::RichText::new(format!("{} · {}", batch.code, batch.stage)).size(9.0).color(MUTED));
            });
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                ui.label(egui::RichText::new(&batch.volume).size(10.0).color(ACCENT));
            });
        });
        ui.add_space(5.0);
        ui.add(egui::ProgressBar::new(batch.progress).desired_height(5.0).show_percentage());
    });
    ui.add_space(5.0);
}

fn attention_row(ui: &mut egui::Ui, code: &str, task: &str, when: &str, color: egui::Color32) {
    egui::Frame::new().fill(CARD).corner_radius(8).inner_margin(10.0).show(ui, |ui| {
        ui.horizontal(|ui| {
            ui.label(egui::RichText::new("●").color(color));
            ui.vertical(|ui| {
                ui.label(egui::RichText::new(task).size(10.0).strong().color(TEXT));
                ui.label(egui::RichText::new(code).size(9.0).color(MUTED));
            });
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                ui.label(egui::RichText::new(when).size(9.0).color(color));
            });
        });
    });
    ui.add_space(5.0);
}

fn draw_demo_chart(ui: &mut egui::Ui) {
    let (rect, _) = ui.allocate_exact_size(egui::vec2(ui.available_width(), 118.0), egui::Sense::hover());
    let painter = ui.painter_at(rect);
    let left = rect.left() + 8.0;
    let right = rect.right() - 8.0;
    let top = rect.top() + 8.0;
    let bottom = rect.bottom() - 12.0;

    for i in 0..4 {
        let y = top + (bottom - top) * i as f32 / 3.0;
        painter.line_segment([egui::pos2(left, y), egui::pos2(right, y)], egui::Stroke::new(1.0, CARD_ALT));
    }

    let values = [0.18, 0.25, 0.31, 0.39, 0.47, 0.53, 0.64, 0.72, 0.78, 0.84];
    let points: Vec<egui::Pos2> = values.iter().enumerate().map(|(i, value)| {
        egui::pos2(
            left + (right - left) * i as f32 / (values.len() - 1) as f32,
            bottom - (bottom - top) * value,
        )
    }).collect();
    painter.add(egui::Shape::line(points, egui::Stroke::new(2.2, ACCENT)));
    painter.text(
        egui::pos2(left, rect.bottom() - 2.0),
        egui::Align2::LEFT_BOTTOM,
        "День 1",
        egui::FontId::proportional(9.0),
        MUTED,
    );
    painter.text(
        egui::pos2(right, rect.bottom() - 2.0),
        egui::Align2::RIGHT_BOTTOM,
        "День 10",
        egui::FontId::proportional(9.0),
        MUTED,
    );
}
