"""
Custom menu component to replace Streamlit's default hamburger menu.
Provides a clean, top-right positioned Help link.
"""

import streamlit as st


class CustomMenu:
    """
    A custom menu component that replaces Streamlit's default hamburger menu.
    Displays only a Help link in a modern, minimalist style.
    """
    
    def __init__(self, help_url: str):
        """
        Initialize the CustomMenu.
        
        Args:
            help_url: URL for the help/documentation page
        """
        self.help_url = help_url
    
    def hide_default_menu(self):
        """Hide the default Streamlit hamburger menu."""
        st.markdown("""
            <style>
            /* Hide ONLY the hamburger menu button, keep everything else */
            [data-testid="stMainMenu"] {
                display: none !important;
            }
            
            /* Hide the Deploy button */
            [data-testid="stToolbar"] {
                display: none !important;
            }
            
            /* Hide the sidebar collapse button (<<) to prevent users from hiding sidebar */
            button[kind="header"][data-testid="baseButton-header"] {
                display: none !important;
            }
            
            /* Alternative selector for collapse button */
            [data-testid="stSidebarCollapseButton"] {
                display: none !important;
            }
            
            /* Also hide by aria-label */
            button[aria-label="Close sidebar"] {
                display: none !important;
            }
            </style>
        """, unsafe_allow_html=True)
    
    def render(self):
        """Render the custom menu in the top-right corner."""
        # Hide the default menu
        self.hide_default_menu()
        
        # Inject custom Help link in top-right corner
        st.markdown(f"""
            <style>
            /* Position container in top-right, below header */
            .custom-menu-container {{
                position: fixed;
                top: 3.5rem;
                right: 1rem;
                z-index: 999999;
            }}
            
            /* Help link styling - simple and modern */
            .help-link {{
                color: #31333F;
                text-decoration: none;
                font-size: 0.875rem;
                font-weight: 400;
                padding: 0.5rem 1rem;
                border-radius: 0.375rem;
                transition: background-color 0.2s ease;
                background-color: white;
                border: 1px solid #e6e6e6;
                display: inline-block;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }}
            
            .help-link:hover {{
                background-color: #f0f2f6;
                text-decoration: none;
            }}
            </style>
            
            <div class="custom-menu-container">
                <a href="{self.help_url}" target="_blank" class="help-link">Help</a>
            </div>
        """, unsafe_allow_html=True)
