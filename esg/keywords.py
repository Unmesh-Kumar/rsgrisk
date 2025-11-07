ENVIRONMENTAL_KEYWORDS = {
    'emission',
    'emissions',
    'carbon',
    'pollution',
    'climate',
    'waste',
    'deforestation',
    'environment',
    'biodiversity',
    'renewable',
    'sustainability',
    'water scarcity',
    'pipeline leak',
    'oil spill',
    'toxic',
    'greenhouse',
    'air quality',
}

SOCIAL_KEYWORDS = {
    'labour',
    'labor',
    'worker',
    'strike',
    'union',
    'discrimination',
    'harassment',
    'human rights',
    'privacy',
    'safety',
    'fatality',
    'community',
    'protest',
    'diversity',
    'inclusive',
}

GOVERNANCE_KEYWORDS = {
    'governance',
    'board',
    'fraud',
    'bribery',
    'audit',
    'corruption',
    'whistleblower',
    'accounting',
    'transparency',
    'sebi',
    'sec',
    'compliance',
    'tax evasion',
    'money laundering',
    'insider trading',
}

ESG_KEYWORDS = {
    'environment': ENVIRONMENTAL_KEYWORDS,
    'social': SOCIAL_KEYWORDS,
    'governance': GOVERNANCE_KEYWORDS,
}

ALL_KEYWORDS = set().union(*ESG_KEYWORDS.values())

