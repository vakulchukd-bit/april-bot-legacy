"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { getLanguage, type Language } from "../lib/language";


// Canonical public origin for Community invitation links.
const APRIL_PUBLIC_SITE_ORIGIN = (() => {
  const fallback = "https://aprill-web-production.up.railway.app";
  const configured = String(process.env.NEXT_PUBLIC_APP_URL || fallback).trim();
  try {
    const parsed = new URL(configured);
    return parsed.protocol === "https:" && !parsed.username && !parsed.password
      ? parsed.origin
      : fallback;
  } catch {
    return fallback;
  }
})();

type CommunityAttachment = { name: string; size: number; download_url: string };
type CommunityMessage = {
  id: number;
  display_name: string;
  plan: "free" | "premium";
  message: string;
  created_at: string | null;
  is_deleted: boolean;
  is_own: boolean;
  author_april_id?: string;
  attachment: CommunityAttachment | null;
};
type CommunityMember = {
  april_id: string;
  display_name: string;
  plan: "free" | "premium";
  relation: "none" | "friend" | "incoming" | "outgoing";
  is_blocked?: boolean;
};

type CommunityResponse = {
  success?: boolean;
  error?: string;
  messages?: CommunityMessage[];
  members?: CommunityMember[];
  profile?: { display_name?: string; is_custom?: boolean };
  plan?: "free" | "premium";
  max_message_chars?: number;
  max_attachment_bytes?: number;
  is_admin?: boolean;
};

const DISPLAY_NAME_STORAGE_PREFIX = "april_display_name:";
const MAX_UPLOAD_BYTES = 3 * 1024 * 1024;
const MAX_DISPLAY_MESSAGES = 30;
// Community attachments are documents, source code, archives and other files —
// not photos or videos. This is a UI guard; the server remains the security boundary.
const MEDIA_FILE_EXTENSIONS = /\.(?:apng|avif|bmp|gif|jpe?g|png|svg|tiff?|webp|heic|heif|ico|mp4|m4v|mov|avi|mkv|webm|mpeg|mpg|3gp|wmv|flv|ogv)$/i;
function isDisallowedMediaFile(file: File | null): boolean {
  return Boolean(file && (/^(?:image|video)\//i.test(file.type) || MEDIA_FILE_EXTENSIONS.test(file.name)));
}

const COPY: Record<Language, Record<string, string>> = {
  ru: {
    title: "Общий чат April", subtitle: "Сообщество пользователей Free и Premium",
    circleTitle: "Друзья", membersTitle: "Поиск друзей", noMembers: "Пока нет друзей. Пригласите друга по ссылке.", inviteFriend: "Пригласить друга", inviteCopied: "Ссылка-приглашение скопирована.", inviteText: "Присоединяйся к сообществу April", addFriend: "Добавить друга", acceptFriend: "Принять", requestSent: "Запрос отправлен", incomingRequest: "Хочет дружить", openDirect: "Личный диалог", friend: "Друг",
    back: "Назад в профиль", profile: "Ваш ник в сообществе", nickPlaceholder: "Введите ник от 2 до 32 символов",
    saveNick: "Сохранить ник", saving: "Сохранение…", welcome: "Здесь можно задавать вопросы, помогать другим, делиться кодом и файлами.",
    publicNotice: "Сообщения и прикреплённые файлы видны другим участникам сообщества. Не отправляйте пароли, ключи API и личные данные.",
    loading: "Загружаем сообщения…", empty: "Пока сообщений нет. Начните обсуждение первым.",
    placeholder: "Опишите вопрос или поделитесь решением…", attach: "Прикрепить файл", send: "Отправить", sending: "Отправка…",
    fileLimit: "Файл до 3 МБ, хранилище вложений на пользователя — до 30 МБ. Исполняемые файлы запрещены.", download: "Скачать файл", report: "Пожаловаться", delete: "Удалить своё сообщение",
    saved: "Ник сохранён на сервере.", deleted: "Сообщение удалено автором.", sent: "Сообщение опубликовано.", reported: "Жалоба зарегистрирована.",
    error: "Не удалось выполнить действие. Попробуйте ещё раз.", signIn: "Войдите через Google, чтобы участвовать в сообществе.",
    signInButton: "Войти через Google", free: "FREE", premium: "PREMIUM", chars: "символов",
    invalidNick: "Ник должен содержать 2–32 буквы, цифры, пробелы, точки, дефисы или подчёркивания.",
    tooLarge: "Файл превышает 3 МБ.", quota: "Лимит хранилища вложений достигнут. Удалите старые сообщения с файлами.", blocked: "Этот тип файла запрещён для безопасности.", rateLimit: "Слишком часто. Подождите минуту и попробуйте снова.",
    deleteConfirm: "Удалить сообщение и прикреплённый файл?", reportConfirm: "Отправить жалобу на это сообщение?", nameReserved: "Этот ник зарезервирован.",
  },
  ua: {
    title: "Спільний чат April", subtitle: "Спільнота користувачів Free та Premium",
    circleTitle: "Друзі", membersTitle: "Пошук друзів", noMembers: "Поки немає друзів. Запросіть друга за посиланням.", inviteFriend: "Запросити друга", inviteCopied: "Посилання-запрошення скопійовано.", inviteText: "Приєднуйся до спільноти April", addFriend: "Додати друга", acceptFriend: "Прийняти", requestSent: "Запит надіслано", incomingRequest: "Хоче дружити", openDirect: "Особистий діалог", friend: "Друг",
    back: "Назад до профілю", profile: "Ваш нік у спільноті", nickPlaceholder: "Введіть нік від 2 до 32 символів",
    saveNick: "Зберегти нік", saving: "Збереження…", welcome: "Ставте запитання, допомагайте іншим, діліться кодом і файлами.",
    publicNotice: "Повідомлення та файли бачать інші учасники спільноти. Не надсилайте паролі, ключі API та особисті дані.",
    loading: "Завантажуємо повідомлення…", empty: "Повідомлень ще немає. Почніть обговорення першими.",
    placeholder: "Опишіть питання або поділіться рішенням…", attach: "Додати файл", send: "Надіслати", sending: "Надсилання…",
    fileLimit: "Файл до 3 МБ, сховище вкладень на користувача — до 30 МБ. Виконувані файли заборонено.", download: "Завантажити файл", report: "Поскаржитися", delete: "Видалити своє повідомлення",
    saved: "Нік збережено на сервері.", deleted: "Повідомлення видалив автор.", sent: "Повідомлення опубліковано.", reported: "Скаргу зареєстровано.",
    error: "Не вдалося виконати дію. Спробуйте ще раз.", signIn: "Увійдіть через Google, щоб долучитися до спільноти.",
    signInButton: "Увійти через Google", free: "FREE", premium: "PREMIUM", chars: "символів",
    invalidNick: "Нік має містити 2–32 літери, цифри, пробіли, крапки, дефіси або підкреслення.",
    tooLarge: "Файл перевищує 3 МБ.", quota: "Ліміт сховища вкладень досягнуто. Видаліть старі повідомлення з файлами.", blocked: "Цей тип файлу заборонено з міркувань безпеки.", rateLimit: "Занадто часто. Зачекайте хвилину й спробуйте знову.",
    deleteConfirm: "Видалити повідомлення та прикріплений файл?", reportConfirm: "Надіслати скаргу на це повідомлення?", nameReserved: "Цей нік зарезервовано.",
  },
  en: {
    title: "April Community Chat", subtitle: "A shared space for Free and Premium users",
    circleTitle: "Friends", membersTitle: "Search friends", noMembers: "No friends yet. Invite a friend using your link.", inviteFriend: "Invite a friend", inviteCopied: "Invitation link copied.", inviteText: "Join me in the April community", addFriend: "Add friend", acceptFriend: "Accept", requestSent: "Request sent", incomingRequest: "Friend request", openDirect: "Private chat", friend: "Friend",
    back: "Back to profile", profile: "Your community nickname", nickPlaceholder: "Enter a nickname (2–32 characters)",
    saveNick: "Save nickname", saving: "Saving…", welcome: "Ask questions, help other users, and share code and files.",
    publicNotice: "Messages and attached files are visible to other community members. Do not share passwords, API keys, or personal data.",
    loading: "Loading messages…", empty: "No messages yet. Start the discussion.",
    placeholder: "Ask a question or share a solution…", attach: "Attach a file", send: "Send", sending: "Sending…",
    fileLimit: "Files up to 3 MB; 30 MB of active attachments per user. Executable files are blocked.", download: "Download file", report: "Report", delete: "Delete your message",
    saved: "Nickname saved on the server.", deleted: "Message deleted by its author.", sent: "Message posted.", reported: "Report registered.",
    error: "The action failed. Please try again.", signIn: "Sign in with Google to join the community.",
    signInButton: "Sign in with Google", free: "FREE", premium: "PREMIUM", chars: "characters",
    invalidNick: "Use 2–32 letters, numbers, spaces, periods, hyphens, or underscores.",
    tooLarge: "The file exceeds 3 MB.", quota: "Attachment storage limit reached. Delete older messages with files.", blocked: "This file type is blocked for safety.", rateLimit: "You are posting too quickly. Wait a minute and try again.",
    deleteConfirm: "Delete this message and its attached file?", reportConfirm: "Report this message to moderation?", nameReserved: "That nickname is reserved.",
  },
  es: {
    title: "Chat de la comunidad April", subtitle: "Comunidad de usuarios Free y Premium", circleTitle: "Amigos", membersTitle: "Buscar amigos", noMembers: "Aún no tienes amigos. Invita a alguien con tu enlace.", inviteFriend: "Invitar a un amigo", inviteCopied: "Enlace de invitación copiado.", inviteText: "Únete a mi comunidad April", addFriend: "Añadir amigo", acceptFriend: "Aceptar", requestSent: "Solicitud enviada", incomingRequest: "Solicitud de amistad", openDirect: "Chat privado", friend: "Amigo",
    back: "Volver al perfil", profile: "Tu apodo en la comunidad", nickPlaceholder: "Apodo de 2 a 32 caracteres", saveNick: "Guardar apodo", saving: "Guardando…", welcome: "Haz preguntas, ayuda a otros y comparte código y archivos.", publicNotice: "Los mensajes y archivos son visibles para la comunidad. No compartas contraseñas, claves API ni datos personales.", loading: "Cargando mensajes…", empty: "Todavía no hay mensajes. Inicia la conversación.", placeholder: "Haz una pregunta o comparte una solución…", attach: "Adjuntar archivo", send: "Enviar", sending: "Enviando…", fileLimit: "Archivo de hasta 3 MB; máximo 30 MB de archivos activos por usuario. Se bloquean los ejecutables.", download: "Descargar archivo", report: "Denunciar", delete: "Eliminar tu mensaje", saved: "Apodo guardado en el servidor.", deleted: "Mensaje eliminado por su autor.", sent: "Mensaje publicado.", reported: "Denuncia registrada.", error: "No se pudo completar la acción. Inténtalo de nuevo.", signIn: "Inicia sesión con Google para participar.", signInButton: "Iniciar sesión con Google", free: "FREE", premium: "PREMIUM", chars: "caracteres", invalidNick: "Usa entre 2 y 32 letras, números, espacios, puntos, guiones o guiones bajos.", tooLarge: "El archivo supera los 3 MB.", quota: "Se alcanzó el límite de almacenamiento. Elimina mensajes antiguos con archivos.", blocked: "Este tipo de archivo está bloqueado por seguridad.", rateLimit: "Demasiados mensajes. Espera un minuto.", deleteConfirm: "¿Eliminar el mensaje y su archivo?", reportConfirm: "¿Denunciar este mensaje?", nameReserved: "Este apodo está reservado.",
  },
  de: {
    title: "April Community-Chat", subtitle: "Gemeinschaft für Free- und Premium-Nutzer", circleTitle: "Freunde", membersTitle: "Freunde suchen", noMembers: "Noch keine Freunde. Lade jemanden über deinen Link ein.", inviteFriend: "Freund einladen", inviteCopied: "Einladungslink kopiert.", inviteText: "Komm in meine April-Community", addFriend: "Freund hinzufügen", acceptFriend: "Annehmen", requestSent: "Anfrage gesendet", incomingRequest: "Freundschaftsanfrage", openDirect: "Privater Chat", friend: "Freund",
    back: "Zurück zum Profil", profile: "Dein Community-Spitzname", nickPlaceholder: "Spitzname (2–32 Zeichen)", saveNick: "Spitzname speichern", saving: "Speichern…", welcome: "Stelle Fragen, hilf anderen und teile Code und Dateien.", publicNotice: "Nachrichten und Dateien sind für Community-Mitglieder sichtbar. Keine Passwörter, API-Schlüssel oder persönlichen Daten teilen.", loading: "Nachrichten werden geladen…", empty: "Noch keine Nachrichten. Starte die Unterhaltung.", placeholder: "Frage stellen oder Lösung teilen…", attach: "Datei anhängen", send: "Senden", sending: "Wird gesendet…", fileLimit: "Dateien bis 3 MB; maximal 30 MB aktive Anhänge pro Nutzer. Ausführbare Dateien sind gesperrt.", download: "Datei herunterladen", report: "Melden", delete: "Eigene Nachricht löschen", saved: "Spitzname auf dem Server gespeichert.", deleted: "Nachricht vom Autor gelöscht.", sent: "Nachricht veröffentlicht.", reported: "Meldung registriert.", error: "Aktion fehlgeschlagen. Bitte erneut versuchen.", signIn: "Mit Google anmelden, um teilzunehmen.", signInButton: "Mit Google anmelden", free: "FREE", premium: "PREMIUM", chars: "Zeichen", invalidNick: "Verwende 2–32 Buchstaben, Zahlen, Leerzeichen, Punkte, Bindestriche oder Unterstriche.", tooLarge: "Datei ist größer als 3 MB.", quota: "Speicherlimit erreicht. Lösche ältere Nachrichten mit Dateien.", blocked: "Dieser Dateityp ist aus Sicherheitsgründen gesperrt.", rateLimit: "Zu viele Nachrichten. Warte eine Minute.", deleteConfirm: "Nachricht und Datei löschen?", reportConfirm: "Diese Nachricht melden?", nameReserved: "Dieser Spitzname ist reserviert.",
  },
  fr: {
    title: "Chat communautaire April", subtitle: "Communauté des utilisateurs Free et Premium", circleTitle: "Amis", membersTitle: "Rechercher des amis", noMembers: "Pas encore d’amis. Invite quelqu’un avec ton lien.", inviteFriend: "Inviter un ami", inviteCopied: "Lien d’invitation copié.", inviteText: "Rejoins ma communauté April", addFriend: "Ajouter un ami", acceptFriend: "Accepter", requestSent: "Demande envoyée", incomingRequest: "Demande d’ami", openDirect: "Discussion privée", friend: "Ami",
    back: "Retour au profil", profile: "Votre pseudo communautaire", nickPlaceholder: "Pseudo de 2 à 32 caractères", saveNick: "Enregistrer le pseudo", saving: "Enregistrement…", welcome: "Posez des questions, aidez les autres et partagez du code et des fichiers.", publicNotice: "Les messages et fichiers sont visibles par la communauté. Ne partagez ni mots de passe, ni clés API, ni données personnelles.", loading: "Chargement des messages…", empty: "Aucun message. Lancez la discussion.", placeholder: "Posez une question ou partagez une solution…", attach: "Joindre un fichier", send: "Envoyer", sending: "Envoi…", fileLimit: "Fichier jusqu’à 3 Mo ; 30 Mo de pièces jointes actives par utilisateur. Les fichiers exécutables sont bloqués.", download: "Télécharger le fichier", report: "Signaler", delete: "Supprimer votre message", saved: "Pseudo enregistré sur le serveur.", deleted: "Message supprimé par son auteur.", sent: "Message publié.", reported: "Signalement enregistré.", error: "Action impossible. Réessayez.", signIn: "Connectez-vous avec Google pour participer.", signInButton: "Connexion avec Google", free: "FREE", premium: "PREMIUM", chars: "caractères", invalidNick: "Utilisez 2 à 32 lettres, chiffres, espaces, points, tirets ou tirets bas.", tooLarge: "Le fichier dépasse 3 Mo.", quota: "Limite de stockage atteinte. Supprimez d’anciens messages avec fichiers.", blocked: "Ce type de fichier est bloqué pour des raisons de sécurité.", rateLimit: "Trop de messages. Attendez une minute.", deleteConfirm: "Supprimer le message et sa pièce jointe ?", reportConfirm: "Signaler ce message ?", nameReserved: "Ce pseudo est réservé.",
  },
  it: {
    title: "Chat della community April", subtitle: "Community per utenti Free e Premium", circleTitle: "Amici", membersTitle: "Cerca amici", noMembers: "Non hai ancora amici. Invita qualcuno con il tuo link.", inviteFriend: "Invita un amico", inviteCopied: "Link d’invito copiato.", inviteText: "Unisciti alla mia community April", addFriend: "Aggiungi amico", acceptFriend: "Accetta", requestSent: "Richiesta inviata", incomingRequest: "Richiesta di amicizia", openDirect: "Chat privata", friend: "Amico",
    back: "Torna al profilo", profile: "Il tuo nickname nella community", nickPlaceholder: "Nickname di 2–32 caratteri", saveNick: "Salva nickname", saving: "Salvataggio…", welcome: "Fai domande, aiuta gli altri e condividi codice e file.", publicNotice: "Messaggi e file sono visibili alla community. Non condividere password, chiavi API o dati personali.", loading: "Caricamento messaggi…", empty: "Nessun messaggio. Inizia la conversazione.", placeholder: "Fai una domanda o condividi una soluzione…", attach: "Allega file", send: "Invia", sending: "Invio…", fileLimit: "File fino a 3 MB; massimo 30 MB di allegati attivi per utente. I file eseguibili sono bloccati.", download: "Scarica file", report: "Segnala", delete: "Elimina il tuo messaggio", saved: "Nickname salvato sul server.", deleted: "Messaggio eliminato dall’autore.", sent: "Messaggio pubblicato.", reported: "Segnalazione registrata.", error: "Operazione non riuscita. Riprova.", signIn: "Accedi con Google per partecipare.", signInButton: "Accedi con Google", free: "FREE", premium: "PREMIUM", chars: "caratteri", invalidNick: "Usa 2–32 lettere, numeri, spazi, punti, trattini o underscore.", tooLarge: "Il file supera 3 MB.", quota: "Limite di archiviazione raggiunto. Elimina vecchi messaggi con file.", blocked: "Questo tipo di file è bloccato per sicurezza.", rateLimit: "Troppi messaggi. Attendi un minuto.", deleteConfirm: "Eliminare il messaggio e il file allegato?", reportConfirm: "Segnalare questo messaggio?", nameReserved: "Questo nickname è riservato.",
  },
  pl: {
    title: "Czat społeczności April", subtitle: "Społeczność użytkowników Free i Premium", circleTitle: "Znajomi", membersTitle: "Szukaj znajomych", noMembers: "Nie masz jeszcze znajomych. Zaproś kogoś linkiem.", inviteFriend: "Zaproś znajomego", inviteCopied: "Skopiowano link zaproszenia.", inviteText: "Dołącz do mojej społeczności April", addFriend: "Dodaj znajomego", acceptFriend: "Akceptuj", requestSent: "Wysłano zaproszenie", incomingRequest: "Zaproszenie do znajomych", openDirect: "Prywatny czat", friend: "Znajomy",
    back: "Powrót do profilu", profile: "Twój nick w społeczności", nickPlaceholder: "Nick od 2 do 32 znaków", saveNick: "Zapisz nick", saving: "Zapisywanie…", welcome: "Zadawaj pytania, pomagaj innym i udostępniaj kod oraz pliki.", publicNotice: "Wiadomości i pliki widzi społeczność. Nie udostępniaj haseł, kluczy API ani danych osobowych.", loading: "Ładowanie wiadomości…", empty: "Brak wiadomości. Rozpocznij dyskusję.", placeholder: "Zadaj pytanie lub podziel się rozwiązaniem…", attach: "Dołącz plik", send: "Wyślij", sending: "Wysyłanie…", fileLimit: "Pliki do 3 MB; maks. 30 MB aktywnych załączników na użytkownika. Pliki wykonywalne są blokowane.", download: "Pobierz plik", report: "Zgłoś", delete: "Usuń swoją wiadomość", saved: "Nick zapisano na serwerze.", deleted: "Wiadomość usunięta przez autora.", sent: "Wiadomość opublikowana.", reported: "Zgłoszenie zapisano.", error: "Nie udało się wykonać działania. Spróbuj ponownie.", signIn: "Zaloguj się przez Google, aby dołączyć.", signInButton: "Zaloguj przez Google", free: "FREE", premium: "PREMIUM", chars: "znaków", invalidNick: "Wpisz 2–32 litery, cyfry, spacje, kropki, myślniki lub podkreślenia.", tooLarge: "Plik przekracza 3 MB.", quota: "Osiągnięto limit. Usuń starsze wiadomości z plikami.", blocked: "Ten typ pliku jest zablokowany ze względów bezpieczeństwa.", rateLimit: "Wysyłasz zbyt często. Poczekaj minutę.", deleteConfirm: "Usunąć wiadomość i załącznik?", reportConfirm: "Zgłosić tę wiadomość?", nameReserved: "Ten nick jest zarezerwowany.",
  },
  pt: {
    title: "Chat da comunidade April", subtitle: "Comunidade de utilizadores Free e Premium", circleTitle: "Amigos", membersTitle: "Procurar amigos", noMembers: "Ainda não tem amigos. Convide alguém pelo seu link.", inviteFriend: "Convidar amigo", inviteCopied: "Ligação de convite copiada.", inviteText: "Junta-te à minha comunidade April", addFriend: "Adicionar amigo", acceptFriend: "Aceitar", requestSent: "Pedido enviado", incomingRequest: "Pedido de amizade", openDirect: "Chat privado", friend: "Amigo",
    back: "Voltar ao perfil", profile: "O seu nome na comunidade", nickPlaceholder: "Nome com 2–32 caracteres", saveNick: "Guardar nome", saving: "A guardar…", welcome: "Faça perguntas, ajude outros utilizadores e partilhe código e ficheiros.", publicNotice: "As mensagens e os ficheiros são visíveis para a comunidade. Não partilhe palavras-passe, chaves API ou dados pessoais.", loading: "A carregar mensagens…", empty: "Ainda não há mensagens. Inicie a conversa.", placeholder: "Faça uma pergunta ou partilhe uma solução…", attach: "Anexar ficheiro", send: "Enviar", sending: "A enviar…", fileLimit: "Ficheiros até 3 MB; máximo de 30 MB de anexos ativos por utilizador. Ficheiros executáveis bloqueados.", download: "Transferir ficheiro", report: "Denunciar", delete: "Eliminar a sua mensagem", saved: "Nome guardado no servidor.", deleted: "Mensagem eliminada pelo autor.", sent: "Mensagem publicada.", reported: "Denúncia registada.", error: "Não foi possível concluir. Tente novamente.", signIn: "Inicie sessão com Google para participar.", signInButton: "Iniciar sessão com Google", free: "FREE", premium: "PREMIUM", chars: "caracteres", invalidNick: "Use 2–32 letras, números, espaços, pontos, hífenes ou sublinhados.", tooLarge: "O ficheiro excede 3 MB.", quota: "Limite de armazenamento atingido. Elimine mensagens antigas com ficheiros.", blocked: "Este tipo de ficheiro está bloqueado por segurança.", rateLimit: "Demasiadas mensagens. Aguarde um minuto.", deleteConfirm: "Eliminar a mensagem e o ficheiro anexado?", reportConfirm: "Denunciar esta mensagem?", nameReserved: "Este nome está reservado.",
  },
  nl: {
    title: "April-communitychat", subtitle: "Community voor Free- en Premium-gebruikers", circleTitle: "Vrienden", membersTitle: "Vrienden zoeken", noMembers: "Nog geen vrienden. Nodig iemand uit via je link.", inviteFriend: "Nodig een vriend uit", inviteCopied: "Uitnodigingslink gekopieerd.", inviteText: "Word lid van mijn April-community", addFriend: "Vriend toevoegen", acceptFriend: "Accepteren", requestSent: "Verzoek verzonden", incomingRequest: "Vriendschapsverzoek", openDirect: "Privéchat", friend: "Vriend",
    back: "Terug naar profiel", profile: "Je community-naam", nickPlaceholder: "Naam van 2–32 tekens", saveNick: "Naam opslaan", saving: "Opslaan…", welcome: "Stel vragen, help anderen en deel code en bestanden.", publicNotice: "Berichten en bestanden zijn zichtbaar voor de community. Deel geen wachtwoorden, API-sleutels of persoonlijke gegevens.", loading: "Berichten laden…", empty: "Nog geen berichten. Begin het gesprek.", placeholder: "Stel een vraag of deel een oplossing…", attach: "Bestand toevoegen", send: "Verzenden", sending: "Verzenden…", fileLimit: "Bestanden tot 3 MB; maximaal 30 MB actieve bijlagen per gebruiker. Uitvoerbare bestanden zijn geblokkeerd.", download: "Bestand downloaden", report: "Melden", delete: "Eigen bericht verwijderen", saved: "Naam opgeslagen op de server.", deleted: "Bericht verwijderd door de auteur.", sent: "Bericht geplaatst.", reported: "Melding geregistreerd.", error: "Actie mislukt. Probeer het opnieuw.", signIn: "Log in met Google om deel te nemen.", signInButton: "Inloggen met Google", free: "FREE", premium: "PREMIUM", chars: "tekens", invalidNick: "Gebruik 2–32 letters, cijfers, spaties, punten, streepjes of underscores.", tooLarge: "Het bestand is groter dan 3 MB.", quota: "Opslaglimiet bereikt. Verwijder oudere berichten met bestanden.", blocked: "Dit bestandstype is om veiligheidsredenen geblokkeerd.", rateLimit: "Te veel berichten. Wacht een minuut.", deleteConfirm: "Bericht en bijlage verwijderen?", reportConfirm: "Dit bericht melden?", nameReserved: "Deze naam is gereserveerd.",
  },
};


const UI_TEXT: Record<Language, { you: string; block: string; unblock: string; confirmBlock: string; confirmUnblock: string; blockDone: string; unblockDone: string; blocked: string }> = {
  ru: { you: "Вы", block: "Блокировать", unblock: "Разблокировать", confirmBlock: "Скрыть сообщения этого пользователя в общем чате?", confirmUnblock: "Снова показывать сообщения этого пользователя?", blockDone: "Пользователь заблокирован — его сообщения скрыты.", unblockDone: "Пользователь разблокирован.", blocked: "Заблокирован" },
  ua: { you: "Ви", block: "Заблокувати", unblock: "Розблокувати", confirmBlock: "Приховати повідомлення цього користувача у спільному чаті?", confirmUnblock: "Знову показувати повідомлення цього користувача?", blockDone: "Користувача заблоковано — його повідомлення приховано.", unblockDone: "Користувача розблоковано.", blocked: "Заблоковано" },
  en: { you: "You", block: "Block", unblock: "Unblock", confirmBlock: "Hide this user's messages in the community chat?", confirmUnblock: "Show this user's messages again?", blockDone: "User blocked. Their public messages are hidden.", unblockDone: "User unblocked.", blocked: "Blocked" },
  es: { you: "Tú", block: "Bloquear", unblock: "Desbloquear", confirmBlock: "¿Ocultar los mensajes de este usuario en la comunidad?", confirmUnblock: "¿Volver a mostrar sus mensajes?", blockDone: "Usuario bloqueado; sus mensajes están ocultos.", unblockDone: "Usuario desbloqueado.", blocked: "Bloqueado" },
  de: { you: "Du", block: "Blockieren", unblock: "Entsperren", confirmBlock: "Nachrichten dieses Nutzers im Community-Chat ausblenden?", confirmUnblock: "Nachrichten dieses Nutzers wieder anzeigen?", blockDone: "Nutzer blockiert; Nachrichten werden ausgeblendet.", unblockDone: "Nutzer entsperrt.", blocked: "Blockiert" },
  fr: { you: "Vous", block: "Bloquer", unblock: "Débloquer", confirmBlock: "Masquer les messages de cette personne dans le chat public ?", confirmUnblock: "Afficher à nouveau ses messages ?", blockDone: "Utilisateur bloqué ; ses messages sont masqués.", unblockDone: "Utilisateur débloqué.", blocked: "Bloqué" },
  it: { you: "Tu", block: "Blocca", unblock: "Sblocca", confirmBlock: "Nascondere i messaggi di questo utente nella chat pubblica?", confirmUnblock: "Mostrare di nuovo i suoi messaggi?", blockDone: "Utente bloccato; i suoi messaggi sono nascosti.", unblockDone: "Utente sbloccato.", blocked: "Bloccato" },
  pl: { you: "Ty", block: "Zablokuj", unblock: "Odblokuj", confirmBlock: "Ukryć wiadomości tego użytkownika na czacie społeczności?", confirmUnblock: "Ponownie pokazywać jego wiadomości?", blockDone: "Użytkownik zablokowany; jego wiadomości są ukryte.", unblockDone: "Użytkownik odblokowany.", blocked: "Zablokowany" },
  pt: { you: "Você", block: "Bloquear", unblock: "Desbloquear", confirmBlock: "Ocultar as mensagens desta pessoa no chat da comunidade?", confirmUnblock: "Mostrar novamente as mensagens desta pessoa?", blockDone: "Utilizador bloqueado; mensagens ocultas.", unblockDone: "Utilizador desbloqueado.", blocked: "Bloqueado" },
  nl: { you: "Jij", block: "Blokkeren", unblock: "Deblokkeren", confirmBlock: "Berichten van deze gebruiker in de communitychat verbergen?", confirmUnblock: "Berichten van deze gebruiker weer tonen?", blockDone: "Gebruiker geblokkeerd; berichten zijn verborgen.", unblockDone: "Gebruiker gedeblokkeerd.", blocked: "Geblokkeerd" },
};


const PROFILE_UI: Record<Language, { communityTitle: string; personalProfile: string; incomingRequests: string; noIncomingRequests: string; friends: string; noFriends: string; contacts: string; accept: string }> = {
  ru: { communityTitle: "April · Сообщество", personalProfile: "Личный профиль", incomingRequests: "Запросы в друзья", noIncomingRequests: "Новых запросов в друзья нет.", friends: "Друзья", noFriends: "Пока нет подтверждённых друзей.", contacts: "Контакты", accept: "Добавить в друзья" },
  ua: { communityTitle: "April · Спільнота", personalProfile: "Особистий профіль", incomingRequests: "Запити в друзі", noIncomingRequests: "Нових запитів у друзі немає.", friends: "Друзі", noFriends: "Поки немає підтверджених друзів.", contacts: "Контакти", accept: "Додати в друзі" },
  en: { communityTitle: "April · Community", personalProfile: "Personal profile", incomingRequests: "Friend requests", noIncomingRequests: "No new friend requests.", friends: "Friends", noFriends: "No confirmed friends yet.", contacts: "Contacts", accept: "Accept friend" },
  es: { communityTitle: "April · Comunidad", personalProfile: "Perfil personal", incomingRequests: "Solicitudes de amistad", noIncomingRequests: "No hay nuevas solicitudes de amistad.", friends: "Amigos", noFriends: "Aún no hay amigos confirmados.", contacts: "Contactos", accept: "Aceptar amistad" },
  de: { communityTitle: "April · Community", personalProfile: "Persönliches Profil", incomingRequests: "Freundschaftsanfragen", noIncomingRequests: "Keine neuen Freundschaftsanfragen.", friends: "Freunde", noFriends: "Noch keine bestätigten Freunde.", contacts: "Kontakte", accept: "Freund hinzufügen" },
  fr: { communityTitle: "April · Communauté", personalProfile: "Profil personnel", incomingRequests: "Demandes d’amitié", noIncomingRequests: "Aucune nouvelle demande d’amitié.", friends: "Amis", noFriends: "Aucun ami confirmé pour le moment.", contacts: "Contacts", accept: "Accepter" },
  it: { communityTitle: "April · Community", personalProfile: "Profilo personale", incomingRequests: "Richieste di amicizia", noIncomingRequests: "Nessuna nuova richiesta di amicizia.", friends: "Amici", noFriends: "Non hai ancora amici confermati.", contacts: "Contatti", accept: "Accetta" },
  pl: { communityTitle: "April · Społeczność", personalProfile: "Profil osobisty", incomingRequests: "Zaproszenia do znajomych", noIncomingRequests: "Brak nowych zaproszeń.", friends: "Znajomi", noFriends: "Brak potwierdzonych znajomych.", contacts: "Kontakty", accept: "Dodaj do znajomych" },
  pt: { communityTitle: "April · Comunidade", personalProfile: "Perfil pessoal", incomingRequests: "Pedidos de amizade", noIncomingRequests: "Não há novos pedidos de amizade.", friends: "Amigos", noFriends: "Ainda não há amigos confirmados.", contacts: "Contactos", accept: "Aceitar amizade" },
  nl: { communityTitle: "April · Community", personalProfile: "Persoonlijk profiel", incomingRequests: "Vriendschapsverzoeken", noIncomingRequests: "Geen nieuwe vriendschapsverzoeken.", friends: "Vrienden", noFriends: "Nog geen bevestigde vrienden.", contacts: "Contacten", accept: "Vriendschap accepteren" },
};

function formatSize(size: number, _language: Language): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(2)} MB`;
}

function formatDate(value: string | null, language: Language): string {
  if (!value) return "";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "";
  const locales: Record<Language, string> = { ru: "ru-RU", ua: "uk-UA", en: "en-US", es: "es-ES", de: "de-DE", fr: "fr-FR", it: "it-IT", pl: "pl-PL", pt: "pt-PT", nl: "nl-NL" };
  return date.toLocaleString(locales[language] || "en-US", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

function errorText(error: string, t: Record<string, string>): string {
  switch (error) {
    case "INVALID_DISPLAY_NAME": return t.invalidNick;
    case "RESERVED_DISPLAY_NAME": return t.nameReserved;
    case "ATTACHMENT_TOO_LARGE":
    case "ATTACHMENT_TOO_LARGE_OR_EMPTY":
    case "REQUEST_BODY_TOO_LARGE": return t.tooLarge;
    case "ATTACHMENT_TYPE_BLOCKED": return t.blocked;
    case "COMMUNITY_ATTACHMENT_QUOTA_REACHED": return t.quota;
    case "RATE_LIMITED": return t.rateLimit;
    default: return t.error;
  }
}

export default function CommunitySpacePage() {
  const { data: session, status } = useSession();
  const user = session?.user as ({ aprilId?: string | null; authenticated?: boolean; plan?: string; name?: string | null }) | undefined;
  const aprilId = String(user?.aprilId ?? "").trim();
  const authenticated = status === "authenticated" && user?.authenticated === true && Boolean(aprilId);
  const [language, setLanguage] = useState<Language>("en");
  const langKey = language;
  const t = useMemo(() => COPY[langKey], [langKey]);
  const [messages, setMessages] = useState<CommunityMessage[]>([]);
  const [members, setMembers] = useState<CommunityMember[]>([]);
  const [profileOpen, setProfileOpen] = useState(false);
  const [nickname, setNickname] = useState("");
  const [draftNickname, setDraftNickname] = useState("");
  const [messageDraft, setMessageDraft] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [plan, setPlan] = useState<"free" | "premium">("free");
  // The Bot snapshot is the single source of truth for the admin UI. Actual
  // deletion remains independently authorized by the Bot against the DB user.
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [savingNick, setSavingNick] = useState(false);
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const scrollBoxRef = useRef<HTMLDivElement | null>(null);
  const composerRef = useRef<HTMLTextAreaElement | null>(null);
  const followLatestRef = useRef(true);
  const nicknameDirtyRef = useRef(false);
  const inviteHandledRef = useRef("");
  const blockedIdsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    setLanguage(getLanguage(aprilId || null));
    setIsAdmin(false);
  }, [aprilId]);

  useEffect(() => {
    const field = composerRef.current;
    if (!field) return;
    field.style.height = "auto";
    field.style.height = `${Math.min(180, Math.max(30, field.scrollHeight))}px`;
  }, [messageDraft]);

  const loadCommunity = useCallback(async (quiet = false) => {
    if (!authenticated) return;
    try {
      const [response, membersResponse] = await Promise.all([
        fetch("/api/community?limit=30", {
          method: "GET", cache: "no-store", credentials: "same-origin",
          headers: { Accept: "application/json" },
        }),
        fetch("/api/community?view=members", {
          method: "GET", cache: "no-store", credentials: "same-origin",
          headers: { Accept: "application/json" },
        }).catch(() => null),
      ]);
      const payload = await response.json().catch(() => null) as CommunityResponse | null;
      const memberPayload = membersResponse ? await membersResponse.json().catch(() => null) as CommunityResponse | null : null;
      if (membersResponse?.ok && memberPayload?.success === true && Array.isArray(memberPayload.members)) {
        const validMembers = memberPayload.members.filter((member) => member && typeof member.april_id === "string");
        setMembers(validMembers);
        // Client-side guard mirrors the server-side per-user block filter. A blocked
        // author's messages disappear only for this viewer, not for other members.
        blockedIdsRef.current = new Set(validMembers.filter((member) => member.is_blocked).map((member) => member.april_id.toLowerCase()));
      }
      if (!response.ok || payload?.success !== true) throw new Error(payload?.error || "COMMUNITY_LOAD_FAILED");
      const nextMessages = (Array.isArray(payload.messages) ? payload.messages : [])
        .filter((message) => {
          const authorId = String(message?.author_april_id || "").trim().toLowerCase();
          return !authorId || !blockedIdsRef.current.has(authorId);
        })
        .slice(-MAX_DISPLAY_MESSAGES);
      setMessages((previous) => {
        // Keep the same array reference when polling returns the same payload.
        // This avoids needless list remounting and mobile scroll jitter.
        if (previous.length === nextMessages.length && previous.every((item, index) =>
          item.id === nextMessages[index]?.id &&
          item.display_name === nextMessages[index]?.display_name &&
          item.plan === nextMessages[index]?.plan &&
          item.message === nextMessages[index]?.message &&
          item.created_at === nextMessages[index]?.created_at &&
          item.is_deleted === nextMessages[index]?.is_deleted &&
          item.is_own === nextMessages[index]?.is_own &&
          item.author_april_id === nextMessages[index]?.author_april_id &&
          item.attachment?.name === nextMessages[index]?.attachment?.name &&
          item.attachment?.size === nextMessages[index]?.attachment?.size &&
          item.attachment?.download_url === nextMessages[index]?.attachment?.download_url
        )) return previous;
        return nextMessages;
      });
      setPlan(payload.plan === "premium" ? "premium" : "free");
      setIsAdmin(payload.is_admin === true);
      let serverName = String(payload.profile?.display_name || "").trim();
      // Migrate a nickname saved by the previous profile page (localStorage) once,
      // but never overwrite a nickname that is already authoritative on the server.
      if (payload.profile?.is_custom !== true) {
        try {
          const legacyName = String(window.localStorage.getItem(`${DISPLAY_NAME_STORAGE_PREFIX}${aprilId}`) || "").trim();
          if (legacyName && legacyName !== serverName && legacyName.length >= 2 && legacyName.length <= 32 && /^[\p{L}\p{N} _.'’\-]+$/u.test(legacyName)) {
            const migrateResponse = await fetch("/api/community", {
              method: "POST", cache: "no-store", credentials: "same-origin",
              headers: { "Content-Type": "application/json", Accept: "application/json" },
              body: JSON.stringify({ action: "save_profile", display_name: legacyName }),
            });
            const migrated = await migrateResponse.json().catch(() => null);
            if (migrateResponse.ok && migrated?.success === true) serverName = String(migrated.profile?.display_name || legacyName).trim();
          }
        } catch { /* A failed nickname migration must not hide community messages. */ }
      }
      if (serverName) {
        setNickname(serverName);
        if (!nicknameDirtyRef.current) setDraftNickname(serverName);
        try { window.localStorage.setItem(`${DISPLAY_NAME_STORAGE_PREFIX}${aprilId}`, serverName); } catch { /* Server remains authoritative. */ }
      }
      setError("");
    } catch (caught) {
      if (!quiet) setError(errorText(String((caught as Error)?.message || ""), t));
    } finally {
      setLoading(false);
    }
  }, [authenticated, aprilId, t]);

  useEffect(() => {
    if (!authenticated) {
      setLoading(status === "loading");
      return;
    }
    void loadCommunity(false);
    const timer = window.setInterval(() => void loadCommunity(true), 7000);
    return () => window.clearInterval(timer);
  }, [authenticated, loadCommunity, status]);

  useEffect(() => {
    if (!authenticated || !aprilId || typeof window === "undefined") return;
    const inviterId = String(new URLSearchParams(window.location.search).get("invite") || "").trim();
    if (!inviterId || inviterId.toLowerCase() === aprilId.toLowerCase()) return;
    const key = `${aprilId}:${inviterId}`;
    if (inviteHandledRef.current === key) return;
    inviteHandledRef.current = key;
    void (async () => {
      try {
        const response = await fetch("/api/community", {
          method: "POST", cache: "no-store", credentials: "same-origin",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({ action: "send_friend_request", peer_id: inviterId }),
        });
        const payload = await response.json().catch(() => null);
        if (response.ok && payload?.success === true) {
          setNotice(payload?.relation === "friend" ? t.friend : payload?.relation === "incoming" ? t.incomingRequest : t.requestSent);
          await loadCommunity(true);
        }
      } catch { /* A referral must never stop normal community access. */ }
    })();
  }, [authenticated, aprilId, loadCommunity, t]);

  useEffect(() => {
    const box = scrollBoxRef.current;
    if (!box || !followLatestRef.current) return;
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length]);

  async function saveNickname(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(""); setNotice("");
    setSavingNick(true);
    try {
      const response = await fetch("/api/community", {
        method: "POST", cache: "no-store", credentials: "same-origin",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ action: "save_profile", display_name: draftNickname }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok || payload?.success !== true) throw new Error(payload?.error || "PROFILE_SAVE_FAILED");
      const savedName = String(payload.profile?.display_name || draftNickname).trim();
      setNickname(savedName); setDraftNickname(savedName); nicknameDirtyRef.current = false; setNotice(t.saved);
      try { window.localStorage.setItem(`${DISPLAY_NAME_STORAGE_PREFIX}${aprilId}`, savedName); } catch { /* Server remains authoritative. */ }
      await loadCommunity(true);
    } catch (caught) {
      setError(errorText(String((caught as Error)?.message || ""), t));
    } finally {
      setSavingNick(false);
    }
  }

  async function sendMessage(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending) return;
    const text = messageDraft.trim();
    if (!text && !selectedFile) return;
    if (selectedFile && selectedFile.size > MAX_UPLOAD_BYTES) {
      setError(t.tooLarge); return;
    }
    setError(""); setNotice(""); setSending(true);
    try {
      // Use JSON for ordinary text posts. Multipart is reserved for actual
      // attachments, so Free and Premium text messages do not depend on a
      // multipart parser or file transport path.
      let body: BodyInit;
      const headers: Record<string, string> = { Accept: "application/json" };
      if (selectedFile) {
        const form = new FormData();
        form.set("action", "send_message");
        form.set("message", text);
        form.set("file", selectedFile, selectedFile.name);
        body = form;
      } else {
        headers["Content-Type"] = "application/json";
        body = JSON.stringify({ action: "send_message", message: text });
      }
      const response = await fetch("/api/community", {
        method: "POST", cache: "no-store", credentials: "same-origin",
        headers, body,
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok || payload?.success !== true) throw new Error(payload?.error || "MESSAGE_SEND_FAILED");
      setMessageDraft(""); setSelectedFile(null); setNotice(t.sent); followLatestRef.current = true;
      await loadCommunity(true);
      window.setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }), 80);
    } catch (caught) {
      setError(errorText(String((caught as Error)?.message || ""), t));
    } finally {
      setSending(false);
    }
  }

  async function messageAction(action: "delete_message" | "admin_delete_message" | "report_message", messageId: number) {
    if ((action === "delete_message" || action === "admin_delete_message") && !window.confirm(
      action === "admin_delete_message"
        ? (langKey === "ru" ? "Удалить это сообщение для всех участников сообщества?" : langKey === "ua" ? "Видалити це повідомлення для всіх учасників спільноти?" : "Delete this message for everyone in the community?")
        : t.deleteConfirm,
    )) return;
    if (action === "report_message" && !window.confirm(t.reportConfirm)) return;
    setError(""); setNotice("");
    try {
      const response = await fetch("/api/community", {
        method: "POST", cache: "no-store", credentials: "same-origin",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ action, message_id: messageId }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok || payload?.success !== true) throw new Error(payload?.error || "COMMUNITY_ACTION_FAILED");
      if (action === "report_message") setNotice(t.reported);
      else if (action === "admin_delete_message") setNotice(
        langKey === "ru" ? "Сообщение удалено администратором." : langKey === "ua" ? "Повідомлення видалено адміністратором." : "Message removed by an administrator.",
      );
      await loadCommunity(true);
    } catch (caught) {
      setError(errorText(String((caught as Error)?.message || ""), t));
    }
  }

  async function relationAction(member: CommunityMember) {
    if (member.relation === "outgoing") return;
    if (member.relation === "friend") {
      window.location.assign(`/space/direct/${encodeURIComponent(member.april_id)}`);
      return;
    }
    const action = member.relation === "incoming" ? "accept_friend_request" : "send_friend_request";
    setError(""); setNotice("");
    try {
      const response = await fetch("/api/community", {
        method: "POST", cache: "no-store", credentials: "same-origin",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ action, peer_id: member.april_id, requester_id: member.april_id }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok || payload?.success !== true) throw new Error(payload?.error || "FRIEND_ACTION_FAILED");
      if (payload?.relation === "friend") setNotice(t.friend);
      else if (payload?.relation === "incoming") setNotice(t.incomingRequest);
      else setNotice(t.requestSent);
      await loadCommunity(true);
    } catch (caught) {
      setError(errorText(String((caught as Error)?.message || ""), t));
    }
  }

  async function shareCommunity() {
    const shareUrl = `${APRIL_PUBLIC_SITE_ORIGIN}/space${aprilId ? `?invite=${encodeURIComponent(aprilId)}` : ""}`;
    const data = { title: "April Community", text: t.inviteText, url: shareUrl };
    try {
      if (typeof navigator.share === "function") {
        await navigator.share(data);
        return;
      }
    } catch (caught) {
      if ((caught as { name?: string })?.name === "AbortError") return;
    }
    try {
      await navigator.clipboard.writeText(shareUrl);
      setNotice(t.inviteCopied);
    } catch {
      setError(t.error);
    }
  }

  function onMessagesScroll() {
    const box = scrollBoxRef.current;
    if (!box) return;
    followLatestRef.current = box.scrollHeight - box.scrollTop - box.clientHeight < 120;
  }

  const incomingRequests = members
    .filter((member) => member.relation === "incoming" && !member.is_blocked)
    .sort((a, b) => a.display_name.localeCompare(b.display_name));
  const friendContacts = members
    .filter((member) => member.relation === "friend")
    .sort((a, b) => a.display_name.localeCompare(b.display_name))
    .slice(0, 10);
  const otherContacts = members
    .filter((member) => member.relation === "outgoing" || Boolean(member.is_blocked))
    .sort((a, b) => a.display_name.localeCompare(b.display_name))
    .slice(0, 10);
  const friendIds = useMemo(() => new Set(members.filter((member) => member.relation === "friend").map((member) => member.april_id.toLowerCase())), [members]);
  const memberById = useMemo(() => new Map(members.map((member) => [member.april_id.toLowerCase(), member])), [members]);
  const labels = UI_TEXT[langKey];
  const profileUI = PROFILE_UI[langKey];

  async function toggleMemberBlock(memberId: string, currentlyBlocked: boolean) {
    const cleanId = String(memberId || "").trim();
    if (!cleanId || cleanId.toLowerCase() === aprilId.toLowerCase()) return;
    if (!window.confirm(currentlyBlocked ? labels.confirmUnblock : labels.confirmBlock)) return;
    setError(""); setNotice("");
    try {
      const response = await fetch("/api/community", {
        method: "POST", cache: "no-store", credentials: "same-origin",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ action: currentlyBlocked ? "unblock_member" : "block_member", peer_id: cleanId }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok || payload?.success !== true) throw new Error(payload?.error || "COMMUNITY_BLOCK_FAILED");
      setNotice(currentlyBlocked ? labels.unblockDone : labels.blockDone);
      await loadCommunity(true);
    } catch (caught) {
      setError(errorText(String((caught as Error)?.message || ""), t));
    }
  }

  if (status === "loading") {
    return <main className="min-h-screen bg-[#07080d] px-4 py-10 text-zinc-300">{t.loading}</main>;
  }

  if (!authenticated) {
    return (
      <main className="min-h-screen bg-[#07080d] px-4 py-10 text-white">
        <div className="mx-auto max-w-xl rounded-3xl border border-white/10 bg-white/[0.03] p-6 sm:p-8">
          <Link href="/settings" className="text-sm text-zinc-400 hover:text-white">← {t.back}</Link>
          <h1 className="mt-6 text-3xl font-semibold">{t.title}</h1>
          <p className="mt-3 text-zinc-400">{t.signIn}</p>
          <Link href="/" className="mt-6 inline-flex rounded-full border border-[#7dff8f]/30 bg-[#7dff8f]/10 px-5 py-3 font-semibold text-[#bfffc7]">{t.signInButton}</Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-[100dvh] overflow-x-hidden bg-[radial-gradient(circle_at_top,rgba(96,165,250,0.08),transparent_34%),#07080d] px-2 py-2 text-white sm:px-4 sm:py-3">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-2">
        <header className="flex min-h-10 items-center justify-between gap-2 rounded-xl border border-white/[0.07] bg-[#10111a]/75 px-3 py-2">
          <div className="min-w-0">
            <Link href="/settings" aria-label={t.back} title={t.back}
              className="block truncate text-sm font-semibold tracking-tight transition hover:text-[#bfffc7] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7dff8f]/40 sm:text-base">
              {profileUI.communityTitle}
            </Link>
          </div>
          <span className={`shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-extrabold tracking-wide ${plan === "premium" ? "border-emerald-300/25 bg-emerald-300/10 text-emerald-200" : "border-white/10 bg-white/[0.04] text-zinc-300"}`}>
            {plan === "premium" ? t.premium : t.free}
          </span>
        </header>

        <section className="shrink-0 overflow-hidden rounded-xl border border-[#60a5fa]/20 bg-[#10111a]/85 shadow-[0_0_18px_rgba(59,130,246,0.04)]">
          <button type="button" onClick={() => setProfileOpen((open) => !open)} aria-expanded={profileOpen}
            className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left transition hover:bg-white/[0.025]">
            <span className="flex min-w-0 items-center gap-2.5">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[#7dff8f]/30 bg-[#7dff8f]/[0.07] text-xs font-bold text-[#bfffc7]">{(nickname || labels.you).slice(0, 1).toLocaleUpperCase()}</span>
              <span className="min-w-0">
                <span className="block truncate text-xs font-semibold text-zinc-100">{profileUI.personalProfile}</span>
                <span className="block truncate text-[10px] text-zinc-500">{nickname || labels.you} · {aprilId}</span>
              </span>
              {incomingRequests.length > 0 && <span className="relative ml-1 flex h-3 w-3 shrink-0" title={`${incomingRequests.length} ${profileUI.incomingRequests}`} aria-label={`${incomingRequests.length} ${profileUI.incomingRequests}`}>
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-yellow-300 opacity-80" />
                <span className="relative inline-flex h-3 w-3 rounded-full bg-yellow-300 shadow-[0_0_12px_rgba(253,224,71,0.9)]" />
              </span>}
              {incomingRequests.length > 0 && <span className="shrink-0 rounded-full border border-yellow-300/30 bg-yellow-300/10 px-2 py-0.5 text-[10px] font-bold text-yellow-200">{incomingRequests.length}</span>}
            </span>
            <span className="shrink-0 text-zinc-500" aria-hidden="true">{profileOpen ? "⌃" : "⌄"}</span>
          </button>

          {profileOpen && <div className="border-t border-white/[0.06] p-3 sm:p-4">
            <div className="grid min-w-0 gap-4 md:grid-cols-2">
              <div className="min-w-0 rounded-xl border border-white/[0.07] bg-black/15 p-3 sm:p-4">
                <form onSubmit={saveNickname} className="flex flex-col gap-2.5">
                  <label htmlFor="community-nickname" className="text-sm font-semibold text-zinc-200">{t.profile}</label>
                  <input id="community-nickname" type="text" autoComplete="nickname" maxLength={32} value={draftNickname}
                    onChange={(event) => { nicknameDirtyRef.current = true; setDraftNickname(event.target.value); }} placeholder={t.nickPlaceholder}
                    className="w-full min-w-0 rounded-xl border border-white/10 bg-black/20 px-3 py-2.5 text-sm text-white outline-none transition placeholder:text-zinc-600 focus:border-[#7dff8f]/40 focus:ring-2 focus:ring-[#7dff8f]/10" />
                  <button type="submit" disabled={savingNick || draftNickname.trim() === nickname.trim() || draftNickname.trim().length < 2}
                    className="rounded-xl border border-[#7dff8f]/25 bg-[#7dff8f]/10 px-4 py-2.5 text-sm font-semibold text-[#bfffc7] transition hover:bg-[#7dff8f]/15 disabled:cursor-not-allowed disabled:opacity-45">
                    {savingNick ? t.saving : t.saveNick}
                  </button>
                </form>
                <button type="button" onClick={() => void shareCommunity()} className="mt-3 w-full rounded-xl border border-[#7dff8f]/25 bg-[#7dff8f]/[0.06] px-3 py-2.5 text-sm font-semibold text-[#bfffc7] transition hover:bg-[#7dff8f]/[0.12]">＋ {t.inviteFriend}</button>
              </div>

              <div className="min-w-0 space-y-3">
                <section className={`rounded-xl border p-3 ${incomingRequests.length ? "border-yellow-300/35 bg-yellow-300/[0.045] shadow-[0_0_18px_rgba(250,204,21,0.07)]" : "border-white/[0.07] bg-black/10"}`}>
                  <div className="mb-2 flex items-center gap-2">
                    {incomingRequests.length > 0 && <span className="relative flex h-2.5 w-2.5 shrink-0"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-yellow-300 opacity-80" /><span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-yellow-300" /></span>}
                    <h2 className="text-sm font-semibold text-zinc-100">{profileUI.incomingRequests}</h2>
                    <span className="ml-auto text-xs text-zinc-500">{incomingRequests.length}</span>
                  </div>
                  {incomingRequests.length === 0 ? <p className="text-xs leading-5 text-zinc-500">{profileUI.noIncomingRequests}</p> : <div className="space-y-2">
                    {incomingRequests.slice(0, 10).map((member) => <article key={member.april_id} className="flex min-w-0 items-center gap-2 rounded-lg border border-yellow-300/20 bg-black/15 px-2.5 py-2">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-yellow-300/30 bg-yellow-300/10 text-xs font-bold text-yellow-100">{member.display_name.slice(0, 1).toLocaleUpperCase()}</span>
                      <span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium text-yellow-100">{member.display_name}</span><span className="text-[9px] font-extrabold text-zinc-500">{member.plan === "premium" ? t.premium : t.free}</span></span>
                      <button type="button" onClick={() => void relationAction(member)} className="shrink-0 rounded-lg border border-yellow-300/30 bg-yellow-300/10 px-2.5 py-2 text-xs font-semibold text-yellow-100 hover:bg-yellow-300/15">{profileUI.accept}</button>
                    </article>)}
                  </div>}
                </section>

                <section className="rounded-xl border border-white/[0.07] bg-black/10 p-3">
                  <div className="mb-2 flex items-center justify-between gap-2"><h2 className="text-sm font-semibold text-zinc-100">{profileUI.friends}</h2><span className="text-xs text-zinc-500">{friendContacts.length}</span></div>
                  {friendContacts.length === 0 ? <p className="text-xs leading-5 text-zinc-500">{profileUI.noFriends}</p> : <div className="space-y-1.5">
                    {friendContacts.map((member) => <div key={member.april_id} className="flex min-w-0 items-center gap-2 rounded-lg border border-amber-300/15 bg-amber-300/[0.025] px-2.5 py-2">
                      <span className="min-w-0 flex-1 truncate text-sm text-amber-100" title={member.display_name}>{member.display_name}</span>
                      <span className="shrink-0 rounded-full border border-amber-300/20 px-1.5 py-0.5 text-[9px] font-bold text-amber-100/80">{member.plan === "premium" ? t.premium : t.free}</span>
                      <button type="button" onClick={() => void relationAction(member)} className="shrink-0 rounded-lg border border-amber-300/25 px-2 py-1.5 text-[11px] font-semibold text-amber-100 hover:bg-amber-300/[0.08]">{t.openDirect}</button>
                    </div>)}
                  </div>}
                </section>

                {otherContacts.length > 0 && <section className="rounded-xl border border-white/[0.07] bg-black/10 p-3">
                  <h2 className="mb-2 text-sm font-semibold text-zinc-100">{profileUI.contacts}</h2>
                  <div className="space-y-1.5">{otherContacts.map((member) => <div key={member.april_id} className="flex min-w-0 items-center gap-2 rounded-lg border border-white/[0.06] px-2.5 py-2">
                    <span className="min-w-0 flex-1 truncate text-xs text-zinc-300" title={member.display_name}>{member.display_name}</span>
                    {member.relation === "outgoing" && <span className="shrink-0 text-[10px] text-zinc-500">{t.requestSent}</span>}
                    <button type="button" onClick={() => void toggleMemberBlock(member.april_id, Boolean(member.is_blocked))} className="shrink-0 rounded-lg border border-white/10 px-2 py-1 text-[10px] text-zinc-400 hover:text-white">{member.is_blocked ? labels.unblock : labels.block}</button>
                  </div>)}</div>
                </section>}
              </div>
            </div>
            </div>}
        </section>

        <section className="flex h-[calc(100dvh-132px)] min-h-[330px] min-w-0 flex-col overflow-hidden rounded-xl border border-[#60a5fa]/20 bg-[#10111a]/95 shadow-[0_12px_32px_rgba(0,0,0,0.18)] sm:h-[calc(100dvh-145px)] sm:rounded-2xl">
          <div className="shrink-0 border-b border-white/[0.07] px-3 py-2">
            <div className="flex items-center justify-between gap-3">
              <Link href="/settings" aria-label={t.back} title={t.back}
                className="truncate text-xs font-semibold transition hover:text-[#bfffc7] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7dff8f]/40 sm:text-sm">
                {profileUI.communityTitle}
              </Link>
              <span className="shrink-0 text-xs text-zinc-500">{messages.length}</span>
            </div>
          </div>
          <div ref={scrollBoxRef} onScroll={onMessagesScroll} className="min-h-0 flex-1 space-y-2 overflow-y-auto overscroll-contain px-2 py-2 sm:px-3 sm:py-2">
            {loading ? <p className="py-8 text-center text-sm text-zinc-500">{t.loading}</p> : messages.length === 0 ? <p className="py-12 text-center text-sm text-zinc-500">{t.empty}</p> : messages.map((item, messageIndex) => {
              const authorId = String(item.author_april_id || "").trim();
              const author = authorId ? memberById.get(authorId.toLowerCase()) : undefined;
              const relationTarget: CommunityMember = author || { april_id: authorId, display_name: item.display_name, plan: item.plan, relation: "none" };
              return <article key={item.id} className={`w-[calc(100%-18px)] ${messageIndex % 2 === 0 ? "ml-[18px] mr-0" : "mr-[18px] ml-0"} rounded-xl border px-2.5 py-2 transition-colors ${item.is_own ? "border-[#7dff8f]/35 bg-[#7dff8f]/[0.045] shadow-[0_0_18px_rgba(125,255,143,0.08)]" : friendIds.has(authorId.toLowerCase()) ? "border-amber-300/40 bg-amber-300/[0.035] shadow-[0_0_18px_rgba(250,204,21,0.09)]" : "border-sky-300/25 bg-sky-300/[0.025] shadow-[0_0_14px_rgba(96,165,250,0.07)]"}`}>
                <div className="flex min-w-0 items-center justify-between gap-2">
                  <span className="flex min-w-0 flex-1 items-center gap-1.5 overflow-hidden">
                    <span title={item.display_name} className={`max-w-[45vw] truncate whitespace-nowrap text-xs font-semibold ${item.is_own ? "text-[#bfffc7]" : friendIds.has(authorId.toLowerCase()) ? "text-amber-200" : "text-sky-200"}`}>{item.display_name}</span>
                    <span className={`shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-extrabold tracking-wide ${item.plan === "premium" ? "border border-emerald-300/25 bg-emerald-300/10 text-emerald-200" : "border border-white/10 bg-white/[0.04] text-zinc-400"}`}>{item.plan === "premium" ? t.premium : t.free}</span>
                  </span>
                  <span className="flex shrink-0 items-center gap-1.5">
                    {!item.is_deleted && (item.is_own || (isAdmin && !item.is_own)) && <button
                      type="button"
                      onClick={() => void messageAction(item.is_own ? "delete_message" : "admin_delete_message", item.id)}
                      aria-label={item.is_own ? t.delete : (langKey === "ru" ? "Удалить сообщение пользователя" : langKey === "ua" ? "Видалити повідомлення користувача" : "Delete user message")}
                      className="rounded-md border border-rose-300/20 bg-rose-300/[0.06] px-2 py-1 text-[10px] font-semibold text-rose-200 transition hover:border-rose-300/40 hover:bg-rose-300/[0.13] hover:text-rose-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-300/40"
                    >{item.is_own ? t.delete : (langKey === "ru" ? "Удалить" : langKey === "ua" ? "Видалити" : "Delete")}</button>}
                    <time className="text-[9px] text-zinc-500">{formatDate(item.created_at, langKey)}</time>
                  </span>
                </div>
                {item.is_deleted ? <p className="mt-1 text-xs italic text-zinc-500">{t.deleted}</p> : item.message && <p className="mt-1 whitespace-pre-wrap break-words text-[13px] leading-5 text-zinc-200">{item.message}</p>}
                {item.attachment && <div className="mt-2 flex min-w-0 flex-wrap items-center justify-between gap-2 rounded-lg border border-sky-300/15 bg-sky-300/[0.035] px-2 py-1.5">
                  <div className="flex min-w-0 items-center gap-3"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-sky-300/15 bg-sky-300/[0.06] font-mono text-[9px] text-sky-200">FILE</span><div className="min-w-0"><p className="break-all text-xs text-zinc-200">{item.attachment.name}</p><p className="text-[10px] text-zinc-500">{formatSize(item.attachment.size, langKey)}</p></div></div>
                  <a href={item.attachment.download_url} download className="rounded-lg border border-sky-300/20 px-2 py-1 text-[10px] font-semibold text-sky-200 transition hover:bg-sky-300/[0.07]">{t.download}</a>
                </div>}
                {!item.is_deleted && !item.is_own && !isAdmin && <div className="mt-1.5 flex flex-wrap items-center gap-1 border-t border-white/[0.05] pt-1">
                  {authorId && <button type="button" disabled={relationTarget.relation === "outgoing"} onClick={() => void relationAction(relationTarget)} className={`max-w-[46%] truncate rounded-md border px-2 py-1 text-[9px] font-semibold leading-4 transition disabled:cursor-default disabled:opacity-50 ${relationTarget.relation === "friend" ? "border-amber-300/25 text-amber-100 hover:bg-amber-300/[0.07]" : relationTarget.relation === "incoming" ? "border-yellow-300/30 text-yellow-100 hover:bg-yellow-300/[0.08]" : "border-sky-300/20 text-sky-200 hover:bg-sky-300/[0.06]"}`}>
                    {relationTarget.relation === "friend" ? t.openDirect : relationTarget.relation === "incoming" ? t.acceptFriend : relationTarget.relation === "outgoing" ? t.requestSent : t.addFriend}
                  </button>}
                </div>}
              </article>;
            })}
            <div ref={bottomRef} />
          </div>
          <form onSubmit={sendMessage} className="z-10 shrink-0 border-t border-white/[0.08] bg-[#10111a]/98 p-2 pb-[calc(0.35rem_+_env(safe-area-inset-bottom))] backdrop-blur-xl">
            {selectedFile && <div className="mb-1 flex min-w-0 items-center gap-2 rounded-lg border border-sky-300/20 bg-sky-300/[0.05] px-2 py-1 text-[10px] text-zinc-300"><svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4 shrink-0 text-sky-200" fill="none" stroke="currentColor" strokeWidth="1.8"><path strokeLinecap="round" strokeLinejoin="round" d="m8 12.5 6.5-6.5a3 3 0 0 1 4.2 4.2l-8.4 8.4a5 5 0 0 1-7.1-7.1l8.2-8.2" /></svg><span className="min-w-0 flex-1 truncate">{selectedFile.name} · {formatSize(selectedFile.size, langKey)}</span><button type="button" onClick={() => setSelectedFile(null)} className="shrink-0 px-1 text-zinc-400 hover:text-rose-200" aria-label="Remove file">×</button></div>}
            <div className="flex min-w-0 items-end gap-1.5">
              <label title={t.attach} aria-label={t.attach} className="pointer-events-auto mb-[3px] flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-full border border-white/[0.04] bg-[rgba(42,42,52,0.72)] text-zinc-200 shadow-[0_8px_30px_rgba(0,0,0,0.14)] backdrop-blur-3xl transition hover:text-sky-200">
                <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8"><path strokeLinecap="round" strokeLinejoin="round" d="m8 12.5 6.5-6.5a3 3 0 0 1 4.2 4.2l-8.4 8.4a5 5 0 0 1-7.1-7.1l8.2-8.2" /></svg>
                <input type="file" accept=".txt,.md,.pdf,.zip,.7z,.tar,.gz,.json,.jsonl,.csv,.log,.py,.js,.ts,.tsx,.jsx,.html,.css,.sql,.xml,.yaml,.yml,.toml,.ini,.conf,.env,.lock,.diff,.patch,.java,.kt,.go,.rs,.c,.cpp,.h,.hpp,.php,.rb,.swift,.dart,.sh,.ps1,.bat,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.odt,.ods,.rtf,.ipynb" className="sr-only" onChange={(event) => {
                  const input = event.currentTarget; const file = input.files?.[0] || null; input.value = "";
                  if (file && file.size > MAX_UPLOAD_BYTES) { setError(t.tooLarge); setSelectedFile(null); return; }
                  if (isDisallowedMediaFile(file)) { setError(t.blocked); setSelectedFile(null); return; }
                  setError(""); setSelectedFile(file);
                }} />
              </label>
              <div className="relative flex min-h-[42px] min-w-0 flex-1 items-end rounded-[24px] border border-white/[0.06] bg-[rgba(42,42,52,0.76)] px-2.5 py-1.5 shadow-[0_8px_30px_rgba(0,0,0,0.14)] backdrop-blur-3xl focus-within:border-[#7dff8f]/25 focus-within:shadow-[0_0_20px_rgba(125,255,143,0.08)]">
                <label htmlFor="community-message" className="sr-only">{t.placeholder}</label>
                <textarea ref={composerRef} id="community-message" value={messageDraft} maxLength={4000} rows={1} onChange={(event) => setMessageDraft(event.target.value)} onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); }
                }} placeholder={t.placeholder} className="max-h-[100px] min-h-[28px] w-full resize-none overflow-y-auto bg-transparent px-1 pr-10 text-[13px] leading-6 text-white outline-none placeholder:text-zinc-400" />
                <button type="submit" aria-label={t.send} title={t.send} disabled={sending || (!messageDraft.trim() && !selectedFile)} className={`absolute bottom-[7px] right-[7px] flex h-7 w-7 items-center justify-center rounded-full border border-white/[0.05] backdrop-blur-3xl transition-all duration-300 disabled:cursor-not-allowed ${sending || (!messageDraft.trim() && !selectedFile) ? "bg-[rgba(58,58,68,0.72)] text-zinc-400" : "bg-[rgba(120,255,140,0.22)] text-[#e8ffd9] shadow-[0_0_18px_rgba(120,255,140,0.34),0_0_42px_rgba(120,255,140,0.20)]"}`}>
                  {sending ? <span className="text-xs">…</span> : <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.9"><path strokeLinecap="round" strokeLinejoin="round" d="M5 12h13m-5-5 5 5-5 5" /></svg>}
                </button>
              </div>
            </div>
            <div className="mt-1 flex items-center justify-between gap-2 px-1"><span title={t.fileLimit} className="min-w-0 truncate text-[9px] text-zinc-600">{t.fileLimit}</span><span className="shrink-0 text-[9px] text-zinc-600">{messageDraft.length}/4000</span></div>
          </form>
        </section>

        {(notice || error) && <p role="status" aria-live="polite" className={`pointer-events-none fixed top-[calc(3.5rem_+_env(safe-area-inset-top))] left-3 right-3 z-50 mx-auto max-w-xl rounded-xl border px-3 py-2 text-xs shadow-xl backdrop-blur-xl ${error ? "border-rose-400/25 bg-[#171018]/95 text-rose-200" : "border-emerald-300/25 bg-[#0c1714]/95 text-emerald-200"}`}>{error || notice}</p>}
      </div>
    </main>
  );
}
