from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.clock import Clock, mainthread
from kivy.garden.graph import Graph, MeshLinePlot
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.uix.image import Image
import re
import random
from datetime import datetime
import csv
import os
import requests
import time
from kivy.core.audio import SoundLoader
from functools import partial
from threading import Thread

# Couleurs modernes (Material Design)
PRIMARY_COLOR = get_color_from_hex("#6200EE")
PRIMARY_LIGHT = get_color_from_hex("#03DAC6")
BACKGROUND = get_color_from_hex("#121212")
CARD_COLOR = get_color_from_hex("#1E1E1E")
TEXT_COLOR = get_color_from_hex("#FFFFFF")
ERROR_COLOR = get_color_from_hex("#CF6679")
WARNING_COLOR = get_color_from_hex("#FFA000")
TEMP_COLOR = get_color_from_hex("#FF5252")
VOLTAGE_COLOR = get_color_from_hex("#4FC3F7")
MOTOR_COLORS = [
    get_color_from_hex("#FF5252"),
    get_color_from_hex("#4CAF50"),
    get_color_from_hex("#FFEB3B"),
    get_color_from_hex("#9C27B0")
]

class RoundedButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.color = TEXT_COLOR
        self.size_hint = (None, None)
        self.height = dp(50)
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*PRIMARY_COLOR)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])

class ValidatedInput(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.spacing = dp(2)
        self.error_label = Label(
            text='', 
            size_hint_y=None, 
            height=dp(16), 
            color=ERROR_COLOR,
            font_size=dp(12))
        self.add_widget(self.error_label)
        
    def show_error(self, message):
        self.error_label.text = message
        
    def clear_error(self):
        self.error_label.text = ''

class ThresholdPopup(Popup):
    def __init__(self, motor_id, current_thresholds, callback, **kwargs):
        super().__init__(**kwargs)
        self.title = f"Configurer les seuils - Moteur {motor_id+1}"
        self.size_hint = (0.8, 0.6)
        self.callback = callback
        
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        # Température
        temp_layout = BoxLayout(spacing=dp(10))
        temp_layout.add_widget(Label(text="Température max (°C):", size_hint_x=0.6))
        self.temp_input = TextInput(
            text=str(current_thresholds['temp']),
            multiline=False,
            input_filter='float',
            size_hint_x=0.4)
        temp_layout.add_widget(self.temp_input)
        
        # Tension
        voltage_layout = BoxLayout(spacing=dp(10))
        voltage_layout.add_widget(Label(text="Tension min (V):", size_hint_x=0.6))
        self.voltage_min_input = TextInput(
            text=str(current_thresholds['voltage_min']),
            multiline=False,
            input_filter='float',
            size_hint_x=0.4)
        voltage_layout.add_widget(self.voltage_min_input)
        
        voltage_layout.add_widget(Label(text="Tension max (V):", size_hint_x=0.6))
        self.voltage_max_input = TextInput(
            text=str(current_thresholds['voltage_max']),
            multiline=False,
            input_filter='float',
            size_hint_x=0.4)
        voltage_layout.add_widget(self.voltage_max_input)
        
        # Boutons
        btn_layout = BoxLayout(spacing=dp(10), size_hint_y=0.2)
        cancel_btn = Button(text="Annuler")
        cancel_btn.bind(on_press=self.dismiss)
        save_btn = RoundedButton(text="Enregistrer")
        save_btn.bind(on_press=self.save_thresholds)
        
        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(save_btn)
        
        layout.add_widget(temp_layout)
        layout.add_widget(voltage_layout)
        layout.add_widget(btn_layout)
        
        self.add_widget(layout)
    
    def save_thresholds(self, instance):
        try:
            thresholds = {
                'temp': float(self.temp_input.text),
                'voltage_min': float(self.voltage_min_input.text),
                'voltage_max': float(self.voltage_max_input.text)
            }
            self.callback(thresholds)
            self.dismiss()
        except ValueError:
            pass

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        main_layout = BoxLayout(orientation='vertical', padding=dp(40), spacing=dp(20))
        title = Label(text="Connexion", font_size=dp(24), bold=True, color=TEXT_COLOR)
        
        # Champ email
        email_container = ValidatedInput()
        email_label = Label(text="Email", size_hint_y=None, height=dp(20), color=TEXT_COLOR)
        self.email_input = TextInput(
            hint_text="Entrez votre email", 
            multiline=False, 
            foreground_color=TEXT_COLOR,
            background_normal='',
            background_active='',
            background_color=CARD_COLOR,
            padding=dp(10),
            cursor_color=TEXT_COLOR)
        email_container.add_widget(email_label)
        email_container.add_widget(self.email_input)
        self.email_container = email_container
        
        # Champ mot de passe
        password_container = ValidatedInput()
        password_label = Label(text="Mot de passe", size_hint_y=None, height=dp(20), color=TEXT_COLOR)
        self.password_input = TextInput(
            hint_text="Entrez votre mot de passe", 
            password=True, 
            multiline=False,
            foreground_color=TEXT_COLOR,
            background_normal='',
            background_active='',
            background_color=CARD_COLOR,
            padding=dp(10),
            cursor_color=TEXT_COLOR)
        password_container.add_widget(password_label)
        password_container.add_widget(self.password_input)
        self.password_container = password_container
        
        login_button = RoundedButton(text="Se connecter")
        login_button.bind(on_press=self.validate_form)
        
        main_layout.add_widget(title)
        main_layout.add_widget(email_container)
        main_layout.add_widget(password_container)
        main_layout.add_widget(login_button)
        
        with main_layout.canvas.before:
            Color(*BACKGROUND)
            self.rect = Rectangle(size=Window.size, pos=main_layout.pos)
        
        self.add_widget(main_layout)
    
    def validate_email(self, email):
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return re.match(pattern, email) is not None
    
    def validate_password(self, password):
        return len(password) >= 6
    
    def validate_form(self, instance):
        self.email_container.clear_error()
        self.password_container.clear_error()
        
        email = self.email_input.text.strip()
        password = self.password_input.text.strip()
        
        is_valid = True
        
        if not email:
            self.email_container.show_error("L'email est requis")
            is_valid = False
        elif not self.validate_email(email):
            self.email_container.show_error("Veuillez entrer un email valide")
            is_valid = False
        
        if not password:
            self.password_container.show_error("Le mot de passe est requis")
            is_valid = False
        elif not self.validate_password(password):
            self.password_container.show_error("Le mot de passe doit contenir au moins 6 caractères")
            is_valid = False
        
        if is_valid:
            self.login(email, password)
    
    def login(self, email, password):
        print(f"Connexion réussie avec email: {email}")
        dashboard = self.manager.get_screen('dashboard')
        dashboard.start_data_update()
        self.manager.current = 'dashboard'

class DashboardScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.alert_sound = SoundLoader.load("alert.mp3")
        self.alert_flashing = False
        self.last_alert_time = 0
        self.data_update_event = None
        self.last_update_time = 0
        self.update_interval = 1  # Intervalle de mise à jour en secondes
        self.alert_popup = None  # Référence à la popup d'alerte actuelle
        
        # Configuration initiale
        self.num_motors = 4
        self.data_history_length = 300
        self.thresholds = [{'temp': 85, 'voltage_min': 200, 'voltage_max': 240} for _ in range(self.num_motors)]
        self.alerts = {i: {'temp': False, 'voltage': False} for i in range(self.num_motors)}
        
        # Pré-allocation des données historiques
        self.temp_data = [[] for _ in range(self.num_motors)]
        self.voltage_data = [[] for _ in range(self.num_motors)]
        self.time_points = []
        
        # Layout principal avec onglets
        self.tab_panel = TabbedPanel(do_default_tab=False)
        
        # Créer un onglet pour chaque moteur
        for i in range(self.num_motors):
            tab = TabbedPanelItem(text=f'Moteur {i+1}')
            tab.content = self.create_motor_tab(i)
            self.tab_panel.add_widget(tab)
        
        # Ajouter un onglet pour l'export et la configuration
        config_tab = TabbedPanelItem(text='Configuration')
        config_tab.content = self.create_config_tab()
        self.tab_panel.add_widget(config_tab)
        
        # Style du fond
        with self.tab_panel.canvas.before:
            Color(*BACKGROUND)
            self.rect = Rectangle(size=Window.size, pos=self.tab_panel.pos)
        
        self.add_widget(self.tab_panel)
    
    def start_data_update(self):
        """Démarrer la mise à jour des données"""
        if self.data_update_event is None:
            self.data_update_event = Clock.schedule_interval(self.update_data, self.update_interval)

    def stop_data_update(self):
        """Arrêter la mise à jour des données"""
        if self.data_update_event:
            self.data_update_event.cancel()
            self.data_update_event = None

    def create_motor_tab(self, motor_id):
        tab_layout = BoxLayout(orientation='vertical', spacing=dp(10))
    
        # En-tête avec boutons
        header = BoxLayout(size_hint_y=None, height=dp(60))
        title = Label(text=f"Moteur {motor_id+1}", font_size=dp(22), bold=True, color=TEXT_COLOR)
    
        # Bouton configuration des seuils
        config_btn = Button(
            text="Configurer les seuils",
            size_hint_x=None,
            width=dp(180))
        config_btn.bind(on_press=lambda x: self.show_threshold_popup(motor_id))
    
        header.add_widget(title)
        header.add_widget(config_btn)
        tab_layout.add_widget(header)
    
        # Cartes de données
        cards_layout = BoxLayout(spacing=dp(15), padding=dp(15), size_hint_y=0.25)
    
        # Stocker les cartes dans le dictionnaire
        if not hasattr(self, 'motor_cards'):
            self.motor_cards = {}
    
        self.motor_cards[motor_id] = {
            'temp_card': self.create_data_card(
                "Température", "N/A", f"Moteur {motor_id+1}", TEMP_COLOR, motor_id),
            'voltage_card': self.create_data_card(
                "Tension", "N/A", f"Moteur {motor_id+1}", VOLTAGE_COLOR, motor_id)
        }
    
        cards_layout.add_widget(self.motor_cards[motor_id]['temp_card'])
        cards_layout.add_widget(self.motor_cards[motor_id]['voltage_card'])
    
        tab_layout.add_widget(cards_layout)
    
        # Graphiques
        graphs_layout = BoxLayout(spacing=dp(15), padding=dp(15))
    
        # Stocker les graphiques dans le dictionnaire
        if not hasattr(self, 'motor_graphs'):
            self.motor_graphs = {}
    
        self.motor_graphs[motor_id] = {
            'temp_graph': self.create_graph(
                f"Température (°C) - Moteur {motor_id+1}", 
                TEMP_COLOR,
                motor_id),
            'voltage_graph': self.create_graph(
                f"Tension (V) - Moteur {motor_id+1}", 
                VOLTAGE_COLOR,
                motor_id)
        }
    
        graphs_layout.add_widget(self.motor_graphs[motor_id]['temp_graph'])
        graphs_layout.add_widget(self.motor_graphs[motor_id]['voltage_graph'])
    
        tab_layout.add_widget(graphs_layout)
    
        return tab_layout
    
    def create_data_card(self, title, value, source, color, motor_id):
        card = BoxLayout(orientation='vertical', size_hint=(0.3, None), height=dp(120),
                    padding=dp(15))
    
        with card.canvas.before:
            Color(*CARD_COLOR)
            RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(10)])
    
        title_label = Label(text=title, font_size=dp(16), color=color, halign='left')
        value_label = Label(text=value, font_size=dp(28), bold=True, color=TEXT_COLOR)
        source_label = Label(text=source, font_size=dp(12), color=get_color_from_hex("#AAAAAA"))
    
        # Indicateur d'alerte avec icône
        alert_icon = Image(
            source='attention.png' if os.path.exists('attention.png') else '', 
            size_hint=(None, None),
            size=(dp(24), dp(24)),
            color=WARNING_COLOR,
            allow_stretch=True)
        alert_icon.opacity = 0  # Invisible par défaut
    
        # Stocker les références comme attributs de la carte
        card.value_label = value_label
        card.alert_icon = alert_icon
    
        card.add_widget(title_label)
        card.add_widget(value_label)
        card.add_widget(source_label)
        card.add_widget(alert_icon)
    
        return card
    
    def create_graph(self, title, color, motor_id):
        graph = Graph(
            xlabel='Temps',
            ylabel=title,
            x_ticks_minor=5,
            x_ticks_major=10,
            y_ticks_major=10,
            y_grid_label=True,
            x_grid_label=True,
            padding=dp(20),
            font_size=dp(12),
            x_grid=True,
            y_grid=True,
            xmin=0,
            xmax=self.data_history_length,
            ymin=0,
            ymax=300,
            background_color=CARD_COLOR,
            border_color=[0.3, 0.3, 0.3, 1],
            label_options={'color': TEXT_COLOR},
            tick_color=[0.5, 0.5, 0.5, 1])
        
        plot = MeshLinePlot(color=color)
        graph.add_plot(plot)
        return graph
    
    def create_config_tab(self):
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(20))
        
        # Section export des données
        export_layout = BoxLayout(orientation='vertical', spacing=dp(10))
        export_layout.add_widget(Label(
            text="Export des données", 
            font_size=dp(18), 
            bold=True, 
            color=TEXT_COLOR,
            size_hint_y=None,
            height=dp(30)))
        
        # Sélecteur de moteur pour l'export
        motor_spinner = Spinner(
            text='Sélectionner un moteur',
            values=[f'Moteur {i+1}' for i in range(self.num_motors)],
            size_hint_y=None,
            height=dp(50))
        
        # Format d'export
        format_spinner = Spinner(
            text='CSV',
            values=['CSV', 'TXT'],
            size_hint_y=None,
            height=dp(50))
        
        # Bouton d'export
        export_btn = RoundedButton(text="Exporter les données", size_hint_y=None, height=dp(50))
        export_btn.bind(on_press=lambda x: self.export_data(
            motor_spinner.values.index(motor_spinner.text),
            format_spinner.text))
        
        export_layout.add_widget(motor_spinner)
        export_layout.add_widget(format_spinner)
        export_layout.add_widget(export_btn)
        
        # Section configuration globale
        config_layout = BoxLayout(orientation='vertical', spacing=dp(10))
        config_layout.add_widget(Label(
            text="Configuration globale", 
            font_size=dp(18), 
            bold=True, 
            color=TEXT_COLOR,
            size_hint_y=None,
            height=dp(30)))
        
        # Historique des données
        history_layout = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(50))
        history_layout.add_widget(Label(text="Historique (minutes):", size_hint_x=0.6))
        self.history_input = TextInput(
            text=str(self.data_history_length // 60),
            multiline=False,
            input_filter='int',
            size_hint_x=0.4)
        history_layout.add_widget(self.history_input)
        
        # Bouton sauvegarde configuration
        save_btn = RoundedButton(text="Sauvegarder", size_hint_y=None, height=dp(50))
        save_btn.bind(on_press=self.save_config)
        
        config_layout.add_widget(history_layout)
        config_layout.add_widget(save_btn)
        
        layout.add_widget(export_layout)
        layout.add_widget(config_layout)
        
        return layout
    
    def show_threshold_popup(self, motor_id):
        try:
            response = requests.get(f"http://localhost:8000/api/thresholds/{motor_id + 1}")
            if response.status_code == 200:
                thresholds = response.json()
                current_thresholds = {
                    'temp': thresholds['temp_max'],
                    'voltage_min': thresholds['voltage_min'],
                    'voltage_max': thresholds['voltage_max']
                }
                
                popup = ThresholdPopup(
                    motor_id=motor_id,
                    current_thresholds=current_thresholds,
                    callback=lambda th: self.update_thresholds(motor_id, th))
                popup.open()
        except requests.exceptions.RequestException as e:
            print(f"Erreur de connexion au serveur: {e}")
    
    def update_thresholds(self, motor_id, thresholds):
        try:
            response = requests.post(
                f"http://localhost:8000/api/thresholds/",
                json={
                    "motor_id": motor_id + 1,
                    "temp_max": thresholds['temp'],
                    "voltage_min": thresholds['voltage_min'],
                    "voltage_max": thresholds['voltage_max']
                })
            if response.status_code == 200:
                print(f"Nouveaux seuils enregistrés pour le moteur {motor_id + 1}")
        except requests.exceptions.RequestException as e:
            print(f"Erreur de connexion au serveur: {e}")
    
    def update_data(self, dt):
        current_time = time.time()
        if current_time - self.last_update_time < self.update_interval:
            return
        
        self.last_update_time = current_time
        
        # Utiliser un thread séparé pour les requêtes API
        Thread(target=self.fetch_and_update_data, daemon=True).start()
    
    def fetch_and_update_data(self):
        try:
            for motor_id in range(self.num_motors):
                # Récupérer les données historiques pour chaque moteur
                response = requests.get(f"http://localhost:8000/api/data/{motor_id + 1}/history?limit=1")
                if response.status_code == 200:
                    data = response.json()
                    if data:  # Vérifier si des données sont disponibles
                        latest_data = data[0]
                        self.update_ui_with_data(motor_id, latest_data)
        except requests.exceptions.RequestException as e:
            print(f"Erreur de connexion au serveur: {e}")
    
    @mainthread
    def update_ui_with_data(self, motor_id, latest_data):
        # Mise à jour des données
        self.temp_data[motor_id].append(latest_data['temperature'])
        self.voltage_data[motor_id].append(latest_data['voltage'])
        
        # Vérifier les alertes
        temp_alert = latest_data['temperature'] > self.thresholds[motor_id]['temp']
        voltage_alert = (latest_data['voltage'] < self.thresholds[motor_id]['voltage_min'] or 
                        latest_data['voltage'] > self.thresholds[motor_id]['voltage_max'])
        
        # Mise à jour des états d'alerte
        self.alerts[motor_id]['temp'] = temp_alert
        self.alerts[motor_id]['voltage'] = voltage_alert
        
        # Déclencher ou arrêter les alertes
        if temp_alert or voltage_alert:
            if not self.alert_popup:  # Si aucune alerte n'est déjà active
                self.trigger_alert(motor_id)
        else:
            self.stop_alert()  # Ferme automatiquement la popup si les valeurs sont normales
        
        # Mise à jour de l'interface
        self.update_data_card(motor_id, latest_data['temperature'], latest_data['voltage'])
        self.update_graphs(motor_id)
        
        # Garder seulement les N dernières valeurs
        if len(self.temp_data[motor_id]) > self.data_history_length:
            self.temp_data[motor_id] = self.temp_data[motor_id][-self.data_history_length:]
            self.voltage_data[motor_id] = self.voltage_data[motor_id][-self.data_history_length:]
    
    def update_graphs(self, motor_id):
        # Mise à jour du graphique température
        if len(self.temp_data[motor_id]) > 0:
            temp_plot = self.motor_graphs[motor_id]['temp_graph'].plots[0]
            temp_plot.points = [(i, val) for i, val in enumerate(self.temp_data[motor_id])]
            self.motor_graphs[motor_id]['temp_graph'].ymax = max(self.temp_data[motor_id]) * 1.1
            self.motor_graphs[motor_id]['temp_graph'].ymin = min(self.temp_data[motor_id]) * 0.9
        
        # Mise à jour du graphique tension
        if len(self.voltage_data[motor_id]) > 0:
            voltage_plot = self.motor_graphs[motor_id]['voltage_graph'].plots[0]
            voltage_plot.points = [(i, val) for i, val in enumerate(self.voltage_data[motor_id])]
            self.motor_graphs[motor_id]['voltage_graph'].ymax = max(self.voltage_data[motor_id]) * 1.1
            self.motor_graphs[motor_id]['voltage_graph'].ymin = min(self.voltage_data[motor_id]) * 0.9
    
    def trigger_alert(self, motor_id):
        """Déclenche une alerte visuelle et sonore"""
        # Jouer le son d'alerte
        if self.alert_sound:
            self.alert_sound.play()
    
        # Faire clignoter les cartes du moteur concerné
        self.alert_flashing = True
        Clock.schedule_interval(partial(self.flash_alert, motor_id), 0.5)
    
        # Afficher une notification
        self.show_alert_notification(motor_id)

    def flash_alert(self, motor_id, dt):
        """Fait clignoter les cartes du moteur en alerte"""
        if not self.alert_flashing:
            return False  # Retourne False pour arrêter le schedule
    
        motor_cards = self.motor_cards.get(motor_id, {})
        for card in motor_cards.values():
            card.canvas.before.clear()
            with card.canvas.before:
                if random.random() > 0.5:  # Effet de clignotement aléatoire
                    Color(*ERROR_COLOR)
                else:
                    Color(*CARD_COLOR)
                RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(10)])
        return True

    def show_alert_notification(self, motor_id):
        """Affiche une popup d'alerte qui se fermera automatiquement lorsque les valeurs reviendront à la normale"""
        alerts = []
        if self.alerts[motor_id]['temp']:
            alerts.append(f"Température trop élevée (> {self.thresholds[motor_id]['temp']}°C)")
        if self.alerts[motor_id]['voltage']:
            alerts.append(f"Tension hors limites (< {self.thresholds[motor_id]['voltage_min']}V ou > {self.thresholds[motor_id]['voltage_max']}V)")
    
        if alerts:
            content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
            
            # Ajout de l'icône d'attention
            alert_icon = Image(
                source='attention.png' if os.path.exists('attention.png') else '',
                size_hint=(None, None),
                size=(dp(48), dp(48)),
                color=ERROR_COLOR,
                allow_stretch=True)
            content.add_widget(alert_icon)
            
            content.add_widget(Label(text=f"ALERTE - Moteur {motor_id+1}", font_size=dp(20), color=ERROR_COLOR))
        
            for alert in alerts:
                content.add_widget(Label(text=alert, font_size=dp(16), color=TEXT_COLOR))
        
            content.add_widget(Label(text="Cette alerte se fermera automatiquement lorsque les valeurs reviendront à la normale", 
                                  font_size=dp(14), color=get_color_from_hex("#AAAAAA")))
        
            self.alert_popup = Popup(title='',
                        content=content,
                        size_hint=(0.8, 0.5),
                        auto_dismiss=False)
            self.alert_popup.open()

    def stop_alert(self):
        """Arrête toutes les alertes en cours et ferme la popup si elle existe"""
        if not any(alert['temp'] or alert['voltage'] for alert in self.alerts.values()):
            self.alert_flashing = False
            if self.alert_sound:
                self.alert_sound.stop()
            
            # Fermer la popup d'alerte si elle existe
            if self.alert_popup:
                self.alert_popup.dismiss()
                self.alert_popup = None
            
            # Réinitialiser l'apparence des cartes
            for motor_id in range(self.num_motors):
                cards = self.motor_cards.get(motor_id, {})
                for card in cards.values():
                    card.canvas.before.clear()
                    with card.canvas.before:
                        Color(*CARD_COLOR)
                        RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(10)])
    
    def update_data_card(self, motor_id, temp, voltage):
        # Récupérer les cartes pour ce moteur
        motor_cards = self.motor_cards.get(motor_id, {})
    
        if not motor_cards:
            return
    
        # Mise à jour des cartes de données
        motor_cards['temp_card'].value_label.text = f"{temp:.1f}°C"
        motor_cards['voltage_card'].value_label.text = f"{voltage:.1f}V"
    
        # Mise à jour des indicateurs d'alerte
        motor_cards['temp_card'].alert_icon.opacity = 1 if self.alerts[motor_id]['temp'] else 0
        motor_cards['voltage_card'].alert_icon.opacity = 1 if self.alerts[motor_id]['voltage'] else 0
    
    def export_data(self, motor_id, format):
        filename = f"moteur_{motor_id+1}_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if format == 'CSV':
            filename += ".csv"
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Index', 'Température', 'Tension'])
                for i, (temp, volt) in enumerate(zip(self.temp_data[motor_id], self.voltage_data[motor_id])):
                    writer.writerow([i, temp, volt])
        else:  # TXT
            filename += ".txt"
            with open(filename, 'w') as txtfile:
                txtfile.write("Index\tTempérature\tTension\n")
                for i, (temp, volt) in enumerate(zip(self.temp_data[motor_id], self.voltage_data[motor_id])):
                    txtfile.write(f"{i}\t{temp:.2f}\t{volt:.2f}\n")
        
        print(f"Données exportées vers {filename}")
    
    def save_config(self, instance):
        try:
            minutes = int(self.history_input.text)
            self.data_history_length = minutes * 60
            print(f"Configuration sauvegardée: historique = {minutes} minutes")
        
            # Redémarrer les mises à jour si elles étaient actives
            if self.data_update_event:
                self.stop_data_update()
                self.start_data_update()
        except ValueError:
            pass
    
    def logout(self):
        """Arrêter les mises à jour lors de la déconnexion"""
        self.stop_data_update()
        self.manager.current = 'login'

class MotorDashboardApp(App):
    def build(self):
        Window.clearcolor = BACKGROUND
        
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(DashboardScreen(name='dashboard'))
        
        return sm

if __name__ == '__main__':
    MotorDashboardApp().run()