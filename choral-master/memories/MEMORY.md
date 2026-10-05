# MEMORY — CHORAL MASTER

Projet ChoralMaster à C:\Users\nanga\choral_master\ (Python 3.14, Windows).
Dépendances : music21, mido, midiutil, numpy, Pillow, scipy, pymupdf, pdf2image, pytesseract. OCR d'images via API OMRe (clé helloworld) car le binaire tesseract est indisponible. GUI tkinter. Audio : numpy+wave+winsound (pas pydub/simpleaudio sur 3.14). Cache SHA-256 dans .cache/, preuves dans evidence/<hash>/. Quatre agents vocaux : Soprano, Alto, Ténor, Basse.

Exigences produit (humain) : rendu audio réaliste type live (réverb + humanisation + guitare + piano + métronome), GUI builder pour customiser l'interface, détection des paroles fonctionnelle, support notation Galin-Paris-Chevé, sauvegarde/chargement de projet.

Bugs connus corrigés : 'sr' non défini dans les appels métronome de la GUI (_play) — utiliser SAMPLE_RATE depuis config.py.

Pièges : sur Python 3.14 certains paquets audio classiques sont absents ; vérifier la présence du binaire OCR avant de promettre de la reconnaissance d'image.
§
Bug OMR image_processor.py ligne 149 : `dark_mask` non défini (fautif), corrigé en `bright_mask`. Toujours vérifier après patch — le kernel Python peut servir du bytecode cache périmé ; lancer via terminal frais si l'erreur persiste.
§
Pipeline JPEG partition testé avec succès : OMR → 2 voix détectées (Voice_0 ténor MIDI 61-72, Voice_1 piano MIDI 48-62) → synthèse voix+piano+métronome → WAV 44100Hz 16bit. Fichier rendu : evidence/partition_test_piano_tenor.wav (14.5s).