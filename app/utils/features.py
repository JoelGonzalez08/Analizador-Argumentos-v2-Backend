# Diccionario para cachear análisis de sentimientos (optimización)
import stanza
from sentiment_analysis_spanish import sentiment_analysis
import spacy

sentiment = sentiment_analysis.SentimentAnalysisSpanish()
# Diccionario para cachear análisis de sentimientos (optimización)
vocab_sentim = {}
lemma = {}

nlp = spacy.load("es_core_news_sm")

def caracteristicas(oracion, i, ventana, incluir_sentimiento, lemmatizar):

    # Características del token actual
    token = oracion[i][0]
    postag = oracion[i][1]

    # Características básicas del token actual
    caracteristicas = {
        'bias': 1.0,
        'token.lower()': token.lower(),
        'token.upper()': token.upper(),
        'word[-3:]': token[-3:],
        'word[-2:]': token[-2:],
        'word[-1:]': token[-1:],
        'word[:2]': token[:2],
        'word[:3]': token[:3],
        'word.isupper()': token.isupper(),
        'word.islower()': token.islower(),
        'word.istitle()': token.istitle(),
        'word.isdigit()': token.isdigit(),
        'word.isalpha()': token.isalpha(),
        'word.isalnum()': token.isalnum(),
        'word.length': len(token),
        'word.has_hyphen': '-' in token,
        'word.has_apostrophe': "'" in token,
        'postag': postag,
        'postag[:2]': postag[:2] if len(postag) >= 2 else postag,
    }

    # Análisis de sentimiento (si está habilitado)
    if incluir_sentimiento:
        if token.lower() in vocab_sentim:
            sentim = vocab_sentim[token.lower()]
        else:
            try:
                sentim = sentiment.sentiment(token)
                vocab_sentim[token.lower()] = sentim
            except:
                sentim = 'neutral'  # Fallback si falla el análisis
                vocab_sentim[token.lower()] = sentim

        caracteristicas['sentiment'] = sentim

    # lematización (si está habilitado)
    if lemmatizar:
        if token.lower() in lemma:
            lema = lemma[token.lower()]
        else:
            try:
                doc = nlp(token)
                lema = doc[0].lemma_ if doc else token
                lemma[token.lower()] = lema
            except:
                lema = token
        caracteristicas['lemma'] = lema
    else:
        caracteristicas['lemma'] = token

    # Características de contexto - hacia atrás
    for v in range(1, ventana + 1):
        if i >= v:  # Si existe el token v posiciones atrás
            token_prev = oracion[i-v][0]
            postag_prev = oracion[i-v][1]

            caracteristicas.update({
                f'-{v}:token.lower()': token_prev.lower(),
                f'-{v}:word[-3:]': token_prev[-3:],
                f'-{v}:word[-2:]': token_prev[-2:],
                f'-{v}:word.isupper()': token_prev.isupper(),
                f'-{v}:word.islower()': token_prev.islower(),
                f'-{v}:word.istitle()': token_prev.istitle(),
                f'-{v}:word.isdigit()': token_prev.isdigit(),
                f'-{v}:word.length': len(token_prev),
                f'-{v}:postag': postag_prev,
                f'-{v}:postag[:2]': postag_prev[:2] if len(postag_prev) >= 2 else postag_prev,
            })

            # Sentimiento del token previo
            if incluir_sentimiento:
                if token_prev.lower() in vocab_sentim:
                    sentim_prev = vocab_sentim[token_prev.lower()]
                else:
                    try:
                        sentim_prev = sentiment.sentiment(token_prev)
                        vocab_sentim[token_prev.lower()] = sentim_prev
                    except:
                        sentim_prev = 'neutral'
                        vocab_sentim[token_prev.lower()] = sentim_prev

                caracteristicas[f'-{v}:sentiment'] = sentim_prev

            # lematización del token previo
            if lemmatizar:
                if token_prev.lower() in lemma:
                    lema_prev = lemma[token_prev.lower()]
                else:
                    try:
                        doc_prev = nlp(token_prev)
                        lema_prev = doc_prev[0].lemma_ if doc_prev else token_prev
                        lemma[token_prev.lower()] = lema_prev
                    except:
                        lema_prev = token_prev
                caracteristicas[f'-{v}:lemma'] = lema_prev

        else:
            # Marcadores de inicio de oración
            caracteristicas[f'BOS-{v}'] = True

    # Características de contexto - hacia adelante
    for v in range(1, ventana + 1):
        if i + v < len(oracion):  # Si existe el token v posiciones adelante
            token_next = oracion[i+v][0]
            postag_next = oracion[i+v][1]

            caracteristicas.update({
                f'+{v}:token.lower()': token_next.lower(),
                f'+{v}:word[-3:]': token_next[-3:],
                f'+{v}:word[-2:]': token_next[-2:],
                f'+{v}:word.isupper()': token_next.isupper(),
                f'+{v}:word.islower()': token_next.islower(),
                f'+{v}:word.istitle()': token_next.istitle(),
                f'+{v}:word.isdigit()': token_next.isdigit(),
                f'+{v}:word.length': len(token_next),
                f'+{v}:postag': postag_next,
                f'+{v}:postag[:2]': postag_next[:2] if len(postag_next) >= 2 else postag_next,
            })

            # Sentimiento del token siguiente
            if incluir_sentimiento:
                if token_next.lower() in vocab_sentim:
                    sentim_next = vocab_sentim[token_next.lower()]
                else:
                    try:
                        sentim_next = sentiment.sentiment(token_next)
                        vocab_sentim[token_next.lower()] = sentim_next
                    except:
                        sentim_next = 'neutral'
                        vocab_sentim[token_next.lower()] = sentim_next

                caracteristicas[f'+{v}:sentiment'] = sentim_next

            # lematización del token siguiente
            if lemmatizar:
                if token_next.lower() in lemma:
                    lema_next = lemma[token_next.lower()]
                else:
                    try:
                        doc_next = nlp(token_next)
                        lema_next = doc_next[0].lemma_ if doc_next else token_next
                        lemma[token_next.lower()] = lema_next
                    except:
                        lema_next = token_next
                caracteristicas[f'+{v}:lemma'] = lema_next

        else:
            # Marcadores de final de oración
            caracteristicas[f'EOS-{v}'] = True

    # Características adicionales de bigramas (útiles para argumentos)
    if ventana >= 1:
        # Bigrama con token anterior
        if i > 0:
            bigrama_prev = f"{oracion[i-1][0].lower()}_{token.lower()}"
            caracteristicas['bigrama_prev'] = bigrama_prev

        # Bigrama con token siguiente
        if i < len(oracion) - 1:
            bigrama_next = f"{token.lower()}_{oracion[i+1][0].lower()}"
            caracteristicas['bigrama_next'] = bigrama_next

    # Características de trigramas (si ventana >= 2)
    if ventana >= 2:
        if i > 0 and i < len(oracion) - 1:
            trigrama = f"{oracion[i-1][0].lower()}_{token.lower()}_{oracion[i+1][0].lower()}"
            caracteristicas['trigrama_center'] = trigrama

    return caracteristicas


def sent2features(sent, ventana, incluir_sentimiento, lemma):
    return [caracteristicas(sent, i, ventana, incluir_sentimiento, lemma) for i in range(len(sent))]

def sent2labels(sent):
    return [label for token, pos_tag, label in sent]

def sent2tokens(sent):
    return [token for token, pos_tag, label in sent]
