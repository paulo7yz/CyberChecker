"""
UI Components
Custom UI components for the CyberChecker application
"""

from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.dropdown import DropDown
from kivy.uix.progressbar import ProgressBar
from kivy.graphics import Color, Rectangle


class ModernLabel(Label):
    """
    Custom label with modern styling.
    """
    def __init__(self, **kwargs):
        # Default properties
        self.bold = kwargs.pop('bold', False)
        self.halign = kwargs.pop('halign', 'center')
        self.valign = kwargs.pop('valign', 'middle')
        
        # Make sure there's a color
        if 'color' not in kwargs:
            kwargs['color'] = (0.9, 0.9, 0.9, 1)
        
        super(ModernLabel, self).__init__(**kwargs)
        
        # Update text properties
        self.bind(size=self.update_text_size)
        
    def update_text_size(self, *args):
        """Update text size when size changes."""
        self.text_size = self.width, None


class ModernButton(Button):
    """
    Custom button with modern styling.
    """
    def __init__(self, **kwargs):
        # Default properties
        self.background_normal = ''
        self.background_down = ''
        
        # Make sure there's a background color
        if 'background_color' not in kwargs:
            kwargs['background_color'] = (0.2, 0.2, 0.2, 1)
            
        # Make sure there's a color
        if 'color' not in kwargs:
            kwargs['color'] = (0.9, 0.9, 0.9, 1)
        
        super(ModernButton, self).__init__(**kwargs)
        
        # Add highlight on hover
        self.bind(state=self.update_background)
        
    def update_background(self, instance, value):
        """Update background color based on state."""
        if value == 'down':
            # Darken the button when pressed
            r, g, b, a = self.background_color
            self.background_color = max(0, r - 0.1), max(0, g - 0.1), max(0, b - 0.1), a
        else:
            # Restore original color
            # Note: This assumes the original color is stored somehow or recalculated
            pass


class GradientButton(Button):
    """
    Button with gradient background.
    Since Kivy doesn't natively support gradients, this is a workaround
    using a solid color that changes on press/hover.
    """
    def __init__(self, gradient_colors=None, **kwargs):
        # Default properties
        self.background_normal = ''
        self.background_down = ''
        
        # Default gradient colors (start, end)
        if gradient_colors is None:
            gradient_colors = [(0.2, 0.2, 0.8, 1), (0.1, 0.1, 0.5, 1)]
        self.gradient_colors = gradient_colors
        
        # Set the button color to the middle of the gradient
        r1, g1, b1, a1 = gradient_colors[0]
        r2, g2, b2, a2 = gradient_colors[1]
        middle_color = (
            (r1 + r2) / 2,
            (g1 + g2) / 2,
            (b1 + b2) / 2,
            (a1 + a2) / 2
        )
        
        kwargs['background_color'] = middle_color
        
        # Make sure there's a color
        if 'color' not in kwargs:
            kwargs['color'] = (0.9, 0.9, 0.9, 1)
        
        super(GradientButton, self).__init__(**kwargs)
        
        # Add highlight on hover
        self.bind(state=self.update_background)
        
    def update_background(self, instance, value):
        """Update background color based on state."""
        if value == 'down':
            # Use the end color of the gradient when pressed
            self.background_color = self.gradient_colors[1]
        else:
            # Use the start color of the gradient when normal
            self.background_color = self.gradient_colors[0]


class ModernTextInput(TextInput):
    """
    Custom text input with modern styling.
    """
    def __init__(self, **kwargs):
        # Default properties
        if 'background_color' not in kwargs:
            kwargs['background_color'] = (0.15, 0.15, 0.15, 1)
        
        if 'foreground_color' not in kwargs:
            kwargs['foreground_color'] = (0.9, 0.9, 0.9, 1)
        
        if 'cursor_color' not in kwargs:
            kwargs['cursor_color'] = (0.9, 0.9, 0.9, 1)
        
        super(ModernTextInput, self).__init__(**kwargs)
        
        # Add border effect
        with self.canvas.before:
            Color(0.3, 0.3, 0.3, 1)  # Border color
            self.border = Rectangle(pos=self.pos, size=self.size)
            Color(*self.background_color)  # Interior color
            self.interior = Rectangle(
                pos=(self.pos[0] + 1, self.pos[1] + 1),
                size=(self.size[0] - 2, self.size[1] - 2)
            )
        
        # Update border position and size when widget changes
        self.bind(pos=self.update_graphics, size=self.update_graphics)
    
    def update_graphics(self, *args):
        """Update border and interior graphics."""
        self.border.pos = self.pos
        self.border.size = self.size
        self.interior.pos = (self.pos[0] + 1, self.pos[1] + 1)
        self.interior.size = (self.size[0] - 2, self.size[1] - 2)


class ModernDropDown(DropDown):
    """
    Custom dropdown with modern styling.
    """
    def __init__(self, **kwargs):
        # Default properties
        if 'background_color' not in kwargs:
            self.background_color = (0.2, 0.2, 0.2, 1)
        else:
            self.background_color = kwargs.pop('background_color')
        
        super(ModernDropDown, self).__init__(**kwargs)
        
        # Add background
        with self.canvas.before:
            Color(*self.background_color)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        
        # Update background when dropdown changes
        self.bind(pos=self.update_rect, size=self.update_rect)
    
    def update_rect(self, *args):
        """Update background rectangle."""
        self.rect.pos = self.pos
        self.rect.size = self.size


class ModernSpinner(Spinner):
    """
    Custom spinner with modern styling.
    """
    def __init__(self, **kwargs):
        # Default properties
        self.background_normal = ''
        self.background_down = ''
        
        # Make sure there's a background color
        if 'background_color' not in kwargs:
            kwargs['background_color'] = (0.2, 0.2, 0.2, 1)
            
        # Make sure there's a color
        if 'color' not in kwargs:
            kwargs['color'] = (0.9, 0.9, 0.9, 1)
            
        # Create a custom dropdown
        dropdown = ModernDropDown(background_color=kwargs['background_color'])
        kwargs['dropdown_cls'] = dropdown
        
        super(ModernSpinner, self).__init__(**kwargs)
        
        # Add highlight on hover
        self.bind(state=self.update_background)
        
    def update_background(self, instance, value):
        """Update background color based on state."""
        if value == 'down':
            # Darken the button when pressed
            r, g, b, a = self.background_color
            self.background_color = max(0, r - 0.1), max(0, g - 0.1), max(0, b - 0.1), a
        else:
            # Restore original color
            # Note: This assumes the original color is stored somehow or recalculated
            pass
    
    def _build_dropdown(self, *largs):
        """Override to customize dropdown items."""
        super(ModernSpinner, self)._build_dropdown(*largs)
        
        # Customize dropdown items
        for item in self.dropdown.children:
            if isinstance(item, Button):
                item.background_normal = ''
                item.background_down = ''
                item.background_color = self.background_color
                item.color = self.color
                
                # Add highlight on hover
                item.bind(state=self.update_item_background)
    
    def update_item_background(self, instance, value):
        """Update dropdown item background color based on state."""
        if value == 'down':
            # Darken the button when pressed
            r, g, b, a = self.background_color
            instance.background_color = max(0, r - 0.1), max(0, g - 0.1), max(0, b - 0.1), a
        else:
            # Restore original color
            instance.background_color = self.background_color


class ModernProgressBar(ProgressBar):
    """
    Custom progress bar with modern styling.
    """
    def __init__(self, **kwargs):
        # Default properties
        super(ModernProgressBar, self).__init__(**kwargs)
        
        self.bind(pos=self.update_graphics, size=self.update_graphics)
        
        with self.canvas:
            # Background
            Color(0.1, 0.1, 0.1, 1)
            self.background_rect = Rectangle(pos=self.pos, size=self.size)
            
            # Progress
            Color(0.2, 0.7, 0.2, 1)
            self.progress_rect = Rectangle(
                pos=self.pos,
                size=(self.width * (self.value / self.max), self.height)
            )
    
    def update_graphics(self, *args):
        """Update graphics based on progress."""
        self.canvas.clear()
        
        with self.canvas:
            # Background
            Color(0.1, 0.1, 0.1, 1)
            self.background_rect = Rectangle(pos=self.pos, size=self.size)
            
            # Progress
            Color(0.2, 0.7, 0.2, 1)
            self.progress_rect = Rectangle(
                pos=self.pos,
                size=(self.width * (self.value / self.max), self.height)
            )
    
    def on_value(self, instance, value):
        """Update progress rectangle when value changes."""
        self.progress_rect.size = (self.width * (value / self.max), self.height)


class ResultsPanel(BoxLayout):
    """
    Panel for displaying results (hits, free, etc.)
    """
    def __init__(self, title="Results", **kwargs):
        # Default properties
        super(ResultsPanel, self).__init__(**kwargs)
        
        self.orientation = 'vertical'
        self.padding = 5
        self.spacing = 5
        
        # Add a background
        with self.canvas.before:
            Color(0.15, 0.15, 0.15, 1)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        
        # Update background when panel changes
        self.bind(pos=self.update_rect, size=self.update_rect)
        
        # Add a title
        self.title_label = ModernLabel(
            text=title,
            size_hint=(1, 0.1),
            bold=True,
            color=(0.9, 0.9, 0.9, 1)
        )
        self.add_widget(self.title_label)
        
        # Add a text input for the results
        self.results = ModernTextInput(
            readonly=True,
            multiline=True,
            size_hint=(1, 0.9)
        )
        self.add_widget(self.results)
    
    def update_rect(self, *args):
        """Update background rectangle."""
        self.rect.pos = self.pos
        self.rect.size = self.size
    
    def add_result(self, text):
        """Add a result to the panel."""
        self.results.text += text + '\n'
    
    def clear(self):
        """Clear all results."""
        self.results.text = ''


class StatsPanel(BoxLayout):
    """
    Panel for displaying statistics (CPM, hits, etc.)
    """
    def __init__(self, **kwargs):
        # Default properties
        super(StatsPanel, self).__init__(**kwargs)
        
        self.orientation = 'horizontal'
        self.padding = 5
        self.spacing = 10
        
        # Add a background
        with self.canvas.before:
            Color(0.15, 0.15, 0.15, 1)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        
        # Update background when panel changes
        self.bind(pos=self.update_rect, size=self.update_rect)
        
        # Add stats labels
        # CPM (Checks Per Minute)
        self.cpm_box = BoxLayout(orientation='vertical', size_hint=(0.25, 1))
        self.cpm_label = ModernLabel(text="CPM:", size_hint=(1, 0.4))
        self.cpm_value = ModernLabel(text="0", size_hint=(1, 0.6), font_size=18)
        self.cpm_box.add_widget(self.cpm_label)
        self.cpm_box.add_widget(self.cpm_value)
        
        # Hits
        self.hits_box = BoxLayout(orientation='vertical', size_hint=(0.25, 1))
        self.hits_label = ModernLabel(text="Hits:", size_hint=(1, 0.4))
        self.hits_value = ModernLabel(text="0", size_hint=(1, 0.6), font_size=18)
        self.hits_box.add_widget(self.hits_label)
        self.hits_box.add_widget(self.hits_value)
        
        # Checked / Total
        self.progress_box = BoxLayout(orientation='vertical', size_hint=(0.25, 1))
        self.progress_label = ModernLabel(text="Progress:", size_hint=(1, 0.4))
        self.progress_value = ModernLabel(text="0/0", size_hint=(1, 0.6), font_size=18)
        self.progress_box.add_widget(self.progress_label)
        self.progress_box.add_widget(self.progress_value)
        
        # Elapsed time
        self.time_box = BoxLayout(orientation='vertical', size_hint=(0.25, 1))
        self.time_label = ModernLabel(text="Elapsed:", size_hint=(1, 0.4))
        self.time_value = ModernLabel(text="00:00:00", size_hint=(1, 0.6), font_size=18)
        self.time_box.add_widget(self.time_label)
        self.time_box.add_widget(self.time_value)
        
        # Add all boxes to the panel
        self.add_widget(self.cpm_box)
        self.add_widget(self.hits_box)
        self.add_widget(self.progress_box)
        self.add_widget(self.time_box)
    
    def update_rect(self, *args):
        """Update background rectangle."""
        self.rect.pos = self.pos
        self.rect.size = self.size
    
    def update_cpm(self, value):
        """Update CPM value."""
        self.cpm_value.text = str(value)
    
    def update_hits(self, value):
        """Update hits value."""
        self.hits_value.text = str(value)
    
    def update_progress(self, checked, total):
        """Update progress value."""
        self.progress_value.text = f"{checked}/{total}"
    
    def update_time(self, time_str):
        """Update elapsed time value."""
        self.time_value.text = time_str