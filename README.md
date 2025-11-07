# ESG Risk Insight

A Django-based web application for real-time Environmental, Social, and Governance (ESG) risk analysis of companies using AI-powered web search and scoring.

## Overview

ESG Risk Insight fetches and analyzes ESG-related news items for any company over the past 2 years, providing:
- Comprehensive company overview
- Individual ESG risk items with Environment, Social, and Governance scores
- Weighted overall ESG risk score
- Interactive sorting and filtering capabilities
- User search history tracking

## Features

### Core Functionality
- **AI-Powered News Search**: Uses OpenAI's web search tool to gather recent ESG-related news articles
- **Multi-Dimensional Scoring**: Calculates weighted scores (E=4, S=3, G=3) for each risk item
- **Intelligent Caching**: LRU cache with 1-hour TTL stores results for the last 10 companies
- **User Authentication**: Built-in Django authentication for login/signup
- **Search History**: Tracks last 10 companies searched per user in SQLite

### UI Features
- Human-readable date formatting
- Interactive sorting by:
  - Overall ESG Score (default)
  - Date
  - Environment Score
  - Social Score  
  - Governance Score
- Clickable search history sidebar
- Real-time cache status indication
- Responsive modern design

## Project Structure

```
esgrisk/
├── accounts/              # User authentication (login/signup)
│   ├── forms.py          # Custom signup form
│   ├── views.py          # Auth views
│   └── urls.py           # Auth URL routing
│
├── dashboard/            # Main dashboard interface
│   ├── forms.py          # Company search form
│   ├── views.py          # Dashboard view logic
│   ├── models.py         # SearchHistory model
│   └── urls.py           # Dashboard URL routing
│
├── esg/                  # ESG analysis engine
│   ├── clients.py        # OpenAI web search client
│   ├── services.py       # ESG scoring and analysis logic
│   ├── history.py        # Search history repository
│   ├── keywords.py       # ESG keyword dictionaries
│   ├── utils.py          # Helper functions (parsing, caching)
│   └── exceptions.py     # Custom exceptions
│
├── esgrisk/              # Django project configuration
│   ├── settings.py       # Project settings
│   └── urls.py           # Root URL configuration
│
├── templates/            # HTML templates
│   ├── base.html         # Base template with CSS
│   ├── dashboard/
│   │   └── dashboard.html  # Main dashboard UI
│   └── registration/
│       ├── login.html
│       └── signup.html
│
├── manage.py             # Django management script
├── requirements.txt      # Python dependencies
└── db.sqlite3           # SQLite database
```

## Installation

### Prerequisites
- Python 3.13+
- OpenAI API key

### Setup

1. **Clone the repository**
   ```bash
   cd /path/to/esg/esgrisk
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv esgenv
   source esgenv/bin/activate  # On Windows: esgenv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the project root:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_MODEL=gpt-4o-mini  # Optional, defaults to gpt-4o-mini
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   Open your browser and navigate to `http://127.0.0.1:8000`

## Usage

1. **Sign up / Log in**: Create an account or log in with existing credentials
2. **Search for a company**: Enter a company name in the search box
3. **View ESG profile**: 
   - Company overview (AI-generated)
   - Overall ESG risk score
   - Detailed risk items with individual E/S/G scores
4. **Sort results**: Use the dropdown to sort items by different criteria
5. **Access history**: Click on recent companies in the sidebar to reload their profiles

## Technical Details

### ESG Scoring Algorithm

**Per-Item Score:**
- Each news item receives scores (0-100) for Environment, Social, and Governance aspects
- Overall item score = `(E×4 + S×3 + G×3) / 10`

**Company Overall Score:**
- Average of all item scores
- Weighted by recency and severity

### Caching Strategy
- **Backend**: Django's LocMemCache (in-memory LRU)
- **Capacity**: Last 10 companies
- **TTL**: 1 hour
- **Key**: SHA-1 hash of normalized company name

### Data Models

**SearchHistory (SQLite)**
```python
{
    'user': ForeignKey(User),
    'company_name': CharField(max_length=255),
    'searched_at': DateTimeField
}
```

**Cached ESG Result (In-Memory)**
```python
{
    'company': str,
    'generated_at': ISO timestamp,
    'generated_at_display': Human-readable timestamp,
    'overview': str,
    'overall_score': float,
    'items': [
        {
            'title': str,
            'description': str,
            'date': ISO timestamp,
            'display_date': Human-readable date,
            'source': str,
            'url': str,
            'scores': {
                'environment': float,
                'social': float,
                'governance': float,
                'overall': float
            }
        }
    ],
    'total_items': int,
    'search_window_days': 730
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required) | - |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o-mini` |

### Settings (settings.py)

- `CACHES`: LRU cache configuration (10 items, 1 hour TTL)
- `LOGIN_URL`: Redirect URL for unauthenticated users
- `LOGIN_REDIRECT_URL`: Post-login redirect

## Development

### Running Tests
```bash
python manage.py test
```

### Code Structure
- **Separation of Concerns**: Clear separation between data fetching (clients), business logic (services), and presentation (views/templates)
- **Error Handling**: Graceful degradation when APIs are unavailable
- **Logging**: Comprehensive logging for debugging and monitoring

## Dependencies

- **Django 5.2.8**: Web framework
- **openai ≥1.45.0**: OpenAI API client
- **python-dotenv ≥1.0.1**: Environment variable management
- **python-dateutil ≥2.9.0**: Date parsing utilities

## Security Notes

- **Never commit `.env` files**: Add to `.gitignore`
- **Rotate API keys**: If accidentally exposed, regenerate immediately
- **HTTPS in production**: Always use HTTPS for production deployments
- **SECRET_KEY**: Change Django's SECRET_KEY for production

## License

[Specify your license here]

## Contributing

[Add contribution guidelines if applicable]

## Support

For issues or questions, please [contact information or issue tracker link].

