# Novità di Omoda 9 / Jaecoo per Home Assistant

Cosa cambia a ogni aggiornamento, spiegato in parole semplici.
Le voci più recenti sono in alto. Le versioni indicano la "puntata"
dell'integrazione: aggiorna da **HACS → Omoda 9 / Jaecoo → Aggiorna**.

## [Non rilasciato]

### 🇮🇹 Italiano

- **«Raffredda tutto» ora fa qualcosa anche sulle auto che quel comando non ce l'hanno.** Su alcune vetture il costruttore non autorizza affatto il pulsante unico «raffredda tutto»: premendolo si otteneva soltanto un errore, e non c'era niente da fare. I suoi **pezzi**, però, quella stessa auto li autorizza benissimo, presi uno per uno: il climatizzatore e la ventilazione dei sedili anteriori. Adesso, quando il comando unico è negato, l'integrazione lo rifà da sé in un'unica richiesta che l'auto accetta — la stessa identica cosa che otterresti accendendo a mano il clima e poi i sedili dall'app ufficiale. Quello che la tua vettura non consente resta fuori, e **in «Esito comando» trovi quante funzioni sono rimaste indietro** invece di doverlo indovinare da un sedile che resta tiepido; se nella riga ci sta anche il loro nome te lo scriviamo, e per esteso ci sono comunque sempre nel registro. (Lo spazio è poco davvero: Home Assistant concede 255 caratteri a un messaggio, esito compreso.)
- **Provato su un'auto vera, non solo sulla carta — l'accensione.** Il proprietario di una Jaecoo 7 (l'auto da cui è nata tutta questa storia) ha spedito a mano la richiesta ricomposta a vettura ferma: accettata, ed è uscito a toccare i cuscini — **i due sedili anteriori ventilavano davvero**. Lo **spegnimento** è il gemello simmetrico di quella richiesta, ma quello nessuno l'ha ancora provato: se la tua auto lo rifiutasse, l'interruttore non ti direbbe «spento» per finta — resta com'era e leggi l'errore.
- **Sulla sua auto i sedili posteriori restano fuori, e ci ha detto che non è una rinuncia:** su quella vettura i sedili di dietro non sono né riscaldati né ventilati. Vale la pena dirlo perché lo ha verificato lui a bordo: **noi non possiamo dedurre da questo elenco cosa la tua auto abbia o non abbia montato**, e non ci proviamo.
- **Il freddo sì, il caldo no — e non è una dimenticanza.** «Riscalda tutto» non viene ricomposto allo stesso modo, perché fra le cose che accende c'è il volante riscaldato, e per il volante non sappiamo quale strada alternativa l'auto accetterebbe: tirare a indovinare rischierebbe di far fallire tutto il resto. Su tutte le vetture che conosciamo, del resto, il comando del caldo è già autorizzato e gli basta la potatura che c'era già.
- **Su un'Omoda 9 non cambia assolutamente nulla.** Lì il comando del costruttore è autorizzato e funziona: quando la via ufficiale è aperta non la sostituiamo mai con una nostra imitazione.

### 🇬🇧 English

- **"Cool everything" now does something even on cars that do not have that command.** On some vehicles the manufacturer does not authorise the single "cool everything" button at all: pressing it produced nothing but an error, and there was no way round it. Its **constituent parts**, however, are perfectly authorised on that same car, taken one at a time: the climate control and the front seat ventilation. Now, when the single command is denied, the integration rebuilds it itself into one request the car does accept — exactly the same thing you would get by switching on the climate and then each seat by hand in the official app. Whatever your car does not allow is left out, and **"Command result" tells you how many functions were left behind** instead of leaving you to work it out from a seat that stays lukewarm; if their names fit in the line we write those too, and in full they are always in the log. (Space really is tight: Home Assistant allows a message 255 characters, result included.)
- **Tested on a real car, not only on paper — switching on.** The owner of a Jaecoo 7 (the car this whole story started from) sent the recomposed request by hand with the vehicle parked: accepted — and he went out and put a hand on the cushions: **both front seats really were ventilating**. **Switching off** is the symmetrical twin of that request, but nobody has tried that one yet: if your car refused it, the switch would not falsely claim "off" — it stays as it was and you read the error.
- **On his car the rear seats stay out, and he told us that is no loss:** on that vehicle the rear seats are neither heated nor ventilated. Worth saying because he checked it in the car himself: **we cannot infer from this list what your car does or does not have fitted**, and we do not try.
- **Cooling yes, heating no — and that is not an oversight.** "Heat everything" is not rebuilt the same way, because among the things it switches on is the heated steering wheel, and for the steering wheel we do not know which alternative route the car would accept: guessing could make everything else fail too. On every vehicle we know of, besides, the heating command is already authorised and the pruning that was already there is enough for it.
- **On an Omoda 9 nothing changes at all.** There the manufacturer's command is authorised and works: when the official route is open we never replace it with an imitation of our own.

## v1.13.0 — 2026-08-10

### 🇮🇹 Italiano

- **L'integrazione ora chiede alla tua auto com'è fatta, invece di darlo per scontato.** Alcuni valori erano scritti a mano nel programma perché era così che funzionava l'Omoda 9 su cui è nata: quanto freddo e quanto caldo chiedere con i pulsanti «Raffredda tutto» e «Riscalda tutto», e quanti minuti far durare il climatizzatore. Su un'altra vettura quei numeri possono essere diversi, e nessuno se ne sarebbe accorto. Adesso li legge dalla scheda tecnica che il costruttore invia **insieme al nome dell'auto**: è una risposta che l'integrazione si faceva già mandare, quindi non c'è nessun nuovo tipo di domanda ai server del costruttore.
- **Se imposti una durata che la tua auto non accetta, te lo diciamo.** Il cursore «Durata clima» arriva a 30 minuti, ma non tutte le vetture li accettano: l'Omoda 9, per esempio, ammette solo 5, 10 o 15 minuti. Prima le veniva chiesto un valore che non capiva; adesso si usa il valore ammesso **subito inferiore** a quello che hai scelto — mai uno più lungo, non sarebbe ciò che hai chiesto — e **lo trovi scritto** nell'esito del comando, invece di scoprirlo dal fatto che l'auto si spegne prima.
- **Al primo avvio dopo l'aggiornamento l'integrazione fa una domanda in più all'auto, una volta sola.** Chi ha già l'integrazione installata aveva la scheda tecnica letta con le informazioni di allora, che non comprendevano questi valori: senza rileggerla, la novità qui sopra non sarebbe mai arrivata a chi c'è già. Succede una volta e poi non più.
- **Un limite che preferiamo dirti.** Se la tua auto ammette durate brevi — mettiamo 5 minuti — l'auto spegne il climatizzatore dopo 5 minuti, ma l'interruttore in Home Assistant resta acceso ancora per qualche minuto prima di tornare da solo su «spento». È solo l'interruttore a essere indietro: nessun comando sbagliato parte, e sull'Omoda 9 non capita affatto. Lo sistemeremo con calma, in un aggiornamento che non tocchi anche i comandi del clima.
- **Su un'Omoda 9 non cambia assolutamente nulla.** I valori che il costruttore dichiara per questa vettura sono esattamente quelli che c'erano scritti a mano. Questo aggiornamento serve alle **altre** auto della famiglia: è un pezzo del lavoro per far funzionare l'integrazione anche su Jaecoo e sui modelli solo elettrici.
- **«Raffredda tutto» e «Riscalda tutto»: ora vale sempre l'ultima cosa che hai premuto.** Se spegnevi e subito riaccendevi (o il contrario), i due comandi potevano arrivare all'auto **in ordine invertito**: l'auto partiva e poi si spegneva da sola, mentre l'interruttore restava acceso — e riprovando sembrava che non ripartisse più. Il motivo: prima di mandare il comando l'integrazione deve svegliare l'auto, e l'attesa è molto più lunga se l'auto dorme; la prima pressione la sveglia, così la seconda faceva meno strada e arrivava per prima. Adesso il comando sorpassato viene semplicemente lasciato cadere: all'auto arriva solo l'ultima cosa che hai chiesto.
- **Mentre l'auto si sveglia adesso te lo diciamo.** Per una mezza minuto buono, dopo aver premuto, non compariva nulla: era il silenzio a far ripremere il tasto, cioè proprio la causa del problema qui sopra. Ora nell'«Esito comando» compare *«Sveglio l'auto: il comando parte fra ~35 secondi»*.
- **Dopo un riavvio di Home Assistant l'interruttore non resta più acceso a vuoto.** La preclimatizzazione dura un quarto d'ora e poi l'interruttore si spegne da solo; ma se nel frattempo Home Assistant veniva riavviato — o aggiornavi l'integrazione — quel promemoria andava perso e l'interruttore restava acceso a tempo indeterminato, annunciando qualcosa che l'auto aveva già finito. Ora riprende il conto da dove era rimasto, e se nel frattempo il quarto d'ora è passato si presenta già spento.
- **Se lo spegnimento non riesce, l'interruttore non dice più «spento».** Quando il comando non riusciva a partire, l'interruttore si metteva comunque su spento mentre l'auto continuava tranquillamente a raffreddare. Adesso resta com'era, che è la verità.
- **Quando l'auto spegne la preclimatizzazione, l'interruttore adesso se ne accorge.** «Raffredda tutto» e «Riscalda tutto» non guardavano affatto quello che l'auto racconta di sé: se i due si disallineavano — perché avevi usato l'app ufficiale, perché l'auto aveva finito prima, o perché avevi spento tutto dal cruscotto — l'interruttore restava acceso fino allo scadere del quarto d'ora, e non c'era modo di rimetterlo a posto se non a mano. Ora, quando l'auto comunica che il climatizzatore è spento, l'interruttore la segue. **Solo in quel verso**: il clima acceso per altri motivi non fa comparire da solo un «Raffredda tutto» che non hai chiesto.
- **Gli interruttori non tornano più indietro da soli subito dopo averli premuti.** Accendevi il sedile ventilato, l'interruttore si accendeva, e pochi secondi dopo tornava spento pur essendo il sedile acceso. Succedeva perché bastava un messaggio qualsiasi dell'auto — anche uno che non parlava affatto di quel sedile, come la conferma del comando stesso — per far ricadere l'interruttore sull'ultimo valore misurato, che era quello di prima. Adesso si aspetta che l'auto dica qualcosa **su quella funzione**. Vale per sedili, sbrinamenti, volante, serratura, baule, finestrini, tetto e per la scheda del clima.
- **Un blocco raro che rendeva l'integrazione muta fino al riavvio.** Se un comando veniva interrotto a metà — capita con le automazioni impostate su «riavvia» — il posto in coda non veniva più restituito a nessuno: da quel momento ogni comando successivo, anche premuto giorni dopo, falliva con «L'auto è ancora impegnata coi comandi precedenti» e l'unico rimedio era riavviare Home Assistant. Ora il posto torna libero in ogni caso.
- **Antifurto: dopo ogni comando ricontrolliamo com'è messo davvero.** È l'unica funzione di cui l'auto non manda mai lo stato da sola: finora il valore mostrato era quello letto all'avvio di Home Assistant, e poteva restare sbagliato per tutta la giornata. Adesso, subito dopo aver acceso o spento l'antifurto, l'integrazione richiede al costruttore lo stato aggiornato. **Non cambia quello che vedi sul momento**: quello resta ciò che hai chiesto, perché la risposta arriva prima che l'auto abbia finito di eseguire.
- **Una sola sveglia alla volta.** Quando l'auto dorme va svegliata prima di poterle parlare, e capitava che la preclimatizzazione e l'aggiornamento automatico la svegliassero nello stesso momento, ciascuno per conto suo: la seconda sveglia arrivava a vuoto e l'auto la rifiutava come «sono occupata», rallentando il comando vero. Adesso chi arriva secondo aspetta la sveglia già in corso.
- **Niente più avvisi quando «Raffredda tutto» fa quel che può.** Se usi l'automazione pronta che ti avverte dei comandi non riusciti (il *blueprint* «Avviso comando non riuscito»), fino a ieri ti compariva un avviso a **ogni** pressione di «Raffredda tutto» e «Riscalda tutto»: l'auto ferma accende il climatizzatore ma non i sedili ventilati, e questo veniva segnalato come «eseguito solo in parte». Non è un guasto, è come funziona l'auto — e un avviso che compare sempre e non chiede niente insegna solo a ignorare anche quelli veri. Adesso ricevi il popup **solo quando un comando non parte davvero**. Se quel dettaglio ti interessa c'è una nuova opzione per riaverlo, ed è comunque sempre scritto in «Esito comando».
- **Gli avvisi dei comandi non spariscono più in un lampo.** Quando l'integrazione corregge o salta qualcosa prima di mandare un comando — una durata che la tua auto non accetta, una funzione che il costruttore non autorizza — te lo scrive in «Esito comando». Solo che quel messaggio veniva subito coperto dal passaggio successivo: **misurato sull'auto, restava leggibile 12 millesimi di secondo.** Era scritto, ma nessuno poteva leggerlo. Adesso resta attaccato all'esito del comando e sopravvive anche alla conferma che l'auto manda qualche secondo dopo. Se gli avvisi sono tanti e non entrano tutti nello spazio disponibile, ti diciamo **quanti ne restano fuori** invece di troncarne uno a metà: un avviso tagliato sembra completo, ed è peggio di un avviso assente. Su un'Omoda 9 con le impostazioni normali non compare nulla di nuovo — gli avvisi escono solo quando c'è davvero qualcosa da dire.

### 🇬🇧 English

- **The integration now asks your car how it is built, instead of assuming.** A few values were written by hand in the program, because that is how the Omoda 9 it was born on works: how much cold and how much heat the "Cool everything" and "Heat everything" buttons ask for, and how many minutes the climate control should run. On a different car those numbers can differ, and nobody would have noticed. They are now read from the spec sheet the manufacturer sends **along with the car's name**: a response the integration already asked for, so there is no new kind of request to its servers.
- **If you set a duration your car does not accept, we tell you.** The "Climate duration" slider goes up to 30 minutes, but not every car accepts that: the Omoda 9, for one, only allows 5, 10 or 15. Previously it was sent a value it did not understand; now the allowed value **just below** the one you picked is used — never a longer one, that would not be what you asked for — and **you can read it** in the command result, instead of finding out because the car switched off early.
- **On the first start after this update the integration asks the car one extra question, once only.** If you already have the integration installed, its spec sheet was read back when these values were not being collected: without re-reading it, the change above would never have reached existing users. It happens once and never again.
- **A limitation we would rather tell you about.** If your car only allows short durations — say 5 minutes — the car switches the climate control off after 5 minutes, but the switch in Home Assistant stays on for a few more minutes before returning to "off" by itself. Only the switch lags behind: no wrong command is sent, and on an Omoda 9 it does not happen at all. We will fix it calmly, in an update that does not also touch the climate commands.
- **On an Omoda 9 nothing changes at all.** The values the manufacturer declares for this car are exactly the ones that were hard-coded. This update is for the **other** cars in the family: it is one more piece of the work to make the integration run on Jaecoo and on the battery-only models.
- **"Cool everything" and "Heat everything": the last thing you pressed now always wins.** If you switched off and straight back on (or the other way round), the two commands could reach the car **in reverse order**: the car started up and then shut itself down, while the switch stayed on — and trying again it looked as though it would not restart. The reason: before sending the command the integration has to wake the car, and the wait is far longer when the car is asleep; the first press woke it, so the second had less ground to cover and got there first. The overtaken command is now simply dropped: the car only ever receives the last thing you asked for.
- **We now tell you while the car is being woken.** For a good half minute after pressing, nothing appeared: that silence is what made people press again, which is exactly what caused the problem above. "Command result" now shows *"Waking the car: command goes out in ~35 s"*.
- **After a Home Assistant restart the switch no longer stays on for nothing.** Pre-conditioning runs for a quarter of an hour and then the switch turns itself off; but if Home Assistant was restarted in the meantime — or you updated the integration — that reminder was lost and the switch stayed on indefinitely, announcing something the car had already finished. It now picks the countdown up where it left off, and if the quarter of an hour has passed it comes back already off.
- **If switching off fails, the switch no longer claims "off".** When the command could not go out, the switch went to off anyway while the car carried on cooling. It now stays as it was, which is the truth.
- **When the car ends the pre-conditioning, the switch now notices.** "Cool everything" and "Heat everything" did not look at what the car says about itself at all: once the two drifted apart — because you had used the official app, because the car had finished early, or because you switched everything off from the dashboard — the switch stayed on until the quarter of an hour ran out, with no way to put it right other than by hand. Now, when the car reports the climate control is off, the switch follows. **In that direction only**: climate switched on for other reasons will not conjure up a "Cool everything" you never asked for.
- **Switches no longer flip back on their own moments after you press them.** You turned the ventilated seat on, the switch came on, and a few seconds later it went off again while the seat was actually running. It happened because any message from the car — even one that said nothing about that seat, such as the confirmation of the command itself — made the switch fall back to the last measured value, which was the one from before. It now waits for the car to say something **about that function**. This applies to seats, defrosters, steering wheel, door lock, boot, windows, sunroof and to the climate card.
- **A rare lock-up that left the integration mute until a restart.** If a command was interrupted half-way — which happens with automations set to "restart" — its place in the queue was never handed back: from then on every later command, even one pressed days afterwards, failed with "The car is still busy with previous commands", and the only cure was restarting Home Assistant. The place is now always returned.
- **Alarm: after every command we check what it really did.** It is the one function whose state the car never reports on its own: until now the value shown was the one read when Home Assistant started, and it could stay wrong all day. Now, right after you switch the alarm on or off, the integration asks the manufacturer for the current state. **It does not change what you see at that moment**: that stays what you asked for, because the answer comes back before the car has finished acting on it.
- **One wake-up at a time.** A sleeping car has to be woken before it will listen, and pre-conditioning and the automatic refresh could wake it at the same moment, each unaware of the other: the second wake-up arrived for nothing and the car turned it down as "I am busy", delaying the real command. Whoever arrives second now waits for the wake-up already under way.
- **No more alerts when "Cool everything" does what it can.** If you use the ready-made automation that warns you about failed commands (the "Failed command alert" *blueprint*), until yesterday an alert popped up on **every** press of "Cool everything" and "Heat everything": on a parked car the climate control starts but the ventilated seats do not, and that was reported as "carried out only in part". It is not a fault, it is how the car works — and an alert that always shows up and asks nothing of you only teaches you to ignore the real ones too. You now get the popup **only when a command genuinely fails to go out**. If you care about that detail there is a new option to bring it back, and it is written in "Command result" either way.
- **Command warnings no longer vanish in a flash.** When the integration corrects or skips something before sending a command — a duration your car does not accept, a function the manufacturer does not authorise — it writes so in "Command result". Except that the message was immediately covered by the next step: **measured on the car, it stayed readable for 12 thousandths of a second.** It was written, but nobody could read it. It now stays attached to the command's result and survives the confirmation the car sends a few seconds later. If there are many warnings and they do not all fit in the space available, we tell you **how many are left out** rather than cutting one in half: a truncated warning looks complete, which is worse than a missing one. On an Omoda 9 with normal settings nothing new appears — warnings only come out when there is genuinely something to say.

## v1.12.1 — 2026-08-10

### 🇮🇹 Italiano

- **Nuovo sensore: «Partenza programmata».** L'auto ci mandava già, a ogni collegamento, il piano di partenza impostato dall'app ufficiale — orario e giorni — e noi lo buttavamo via senza guardarlo. Ora lo vedi in Home Assistant: l'orario, i giorni della settimana e se il piano è attivo o spento. **È solo una lettura**: per cambiare il piano si usa ancora l'app. Non aggiunge nessuna richiesta ai server del costruttore, perché è un dato che arrivava già.
- **La ricarica programmata mostra anche il piano che ha davvero l'auto.** Finora l'interruttore mostrava soltanto le preferenze impostate qui dentro: se cambiavi la programmazione dall'app ufficiale, Home Assistant non lo sapeva. Adesso, quando l'auto comunica il suo piano, trovi orario, durata e giorni **come li ha lei**. Compaiono quando l'auto li manda, cioè quando qualcosa cambia: se non ci sono, non vuol dire che non ci sia un piano.
- **Una data che non ti mostriamo, di proposito.** Il piano di partenza arriva accompagnato da un «creato il» e un «modificato il» che sembrano dire quando l'hai impostato. Non lo dicono: il costruttore li riscrive a ogni interrogazione, e infatti risultano sempre di pochi secondi fa. Li abbiamo lasciati fuori, perché un dato inventato che sembra autorevole è peggio di un dato assente.

### 🇬🇧 English

- **New sensor: "Scheduled departure".** The car was already sending us, on every connection, the departure plan you set in the official app — time and days — and we were throwing it away without looking. You can now see it in Home Assistant: the time, the days of the week, and whether the plan is on or off. **It is read-only**: to change the plan you still use the app. It adds no request to the manufacturer's servers, because the data was already arriving.
- **Scheduled charging also shows the plan the car actually holds.** Until now the switch showed only the preferences set in here: if you changed the schedule from the official app, Home Assistant never knew. Now, when the car reports its plan, you get time, duration and days **as the car has them**. They appear when the car sends them, that is when something changes: their absence does not mean there is no plan.
- **One date we deliberately do not show you.** The departure plan arrives with a "created on" and a "modified on" that look like they say when you set it. They do not: the manufacturer rewrites them on every query, which is why they are always a few seconds old. We left them out, because an invented figure that looks authoritative is worse than a missing one.

## v1.12.0 — 2026-08-10

### 🇮🇹 Italiano

- **Nuovo interruttore: «Disappannamento parabrezza».** L'auto sa fare due cose diverse sul vetro davanti, e finora l'integrazione ne offriva una sola. Quella che c'era già, «Sbrinamento parabrezza», **scalda il vetro** con le resistenze elettriche. Questa nuova soffia invece **l'aria del climatizzatore sul parabrezza**, che è il modo rapido per togliere la condensa. Sono comandi distinti e l'auto li tiene separati.
- ⚠️ **Da sapere prima di usarlo: accende anche il climatizzatore** per circa 15 minuti, perché è il climatizzatore stesso a soffiare l'aria sul vetro. Non è un difetto, è come funziona sull'auto. Per lo stesso motivo, spegnere il disappannamento spegne il clima.
- **Antifurto: se la tua auto non lo autorizza, ora te lo dice prima.** Su alcune vetture il costruttore non abilita affatto i comandi dell'antifurto. Prima ricevevi solo un errore, identico a quello di un guasto. Ora l'integrazione ti avvisa che è il costruttore a non permettere quella funzione — così non perdi tempo a cercare un problema che non c'è.
- **Ricarica programmata: avviso quando i giorni scelti non sono ammessi.** Alcune auto accettano solo la programmazione su tutti i giorni della settimana, altre solo su giorni scelti. Se la tua non ammette quella che l'integrazione sta per mandare, adesso lo dice prima invece di lasciarti davanti a un rifiuto senza spiegazione. **Non cambia i giorni al posto tuo**: una ricarica che parte in un giorno che non hai scelto sarebbe peggio di un errore onesto.
- **Un chiarimento su una nostra vecchia nota, per chi legge il codice.** Una verifica approfondita ha fatto sospettare che l'orario della ricarica programmata partisse spostato di un'ora o due rispetto a quello impostato. **Il sospetto è stato controllato ed è infondato: l'orario era ed è corretto.** Nulla cambia nel funzionamento; abbiamo corretto la nota interna che aveva dato origine al dubbio.

### 🇬🇧 English

- **New switch: "Windshield defog".** The car can do two different things to the front glass, and until now the integration offered only one. The existing "Windshield defrost" **heats the glass** with its electric elements. This new one instead blows **the climate system's air onto the windshield**, which is the quick way to clear condensation. They are separate commands and the car keeps them apart.
- ⚠️ **Worth knowing before you use it: it also switches the climate control on** for about 15 minutes, because it is the climate system itself that blows the air onto the glass. This is not a fault, it is how the car works. For the same reason, switching the defog off switches the climate off.
- **Alarm: if your car does not authorise it, you are now told up front.** On some vehicles the manufacturer does not enable the alarm commands at all. You used to get only an error, indistinguishable from a malfunction. The integration now tells you it is the manufacturer withholding the function — so you do not go hunting for a problem that is not there.
- **Scheduled charging: a warning when the chosen days are not allowed.** Some cars accept scheduling on every day of the week only, others only on selected days. If yours does not accept the one the integration is about to send, it now says so beforehand instead of leaving you with an unexplained refusal. **It does not change the days for you**: a charge starting on a day you did not pick would be worse than an honest error.
- **A clarification on an old note of ours, for those who read the code.** A thorough review raised the suspicion that scheduled charging might start one or two hours away from the time you set. **The suspicion was checked and is unfounded: the time was and is correct.** Nothing changes in how it works; we corrected the internal note that caused the doubt.

## v1.11.1 — 2026-08-10

### 🇮🇹 Italiano

- **Correzione alla novità di ieri: su alcune auto non si attivava affatto.** Per decidere se cambiare strada, l'integrazione guardava solo la singola funzione e non l'intera categoria. Su un'auto il cui elenco dei permessi è più corto — cioè che non elenca le singole funzioni ma nega il gruppo intero — concludeva che la strada abituale fosse aperta e non provava quella alternativa: la funzione restava rotta **proprio sulle auto per cui questa novità era stata scritta**. Ora guarda tutte e due.
- **E quando non c'è nulla da fare, adesso te lo dice.** Se il costruttore non autorizza affatto una funzione sulla tua auto, non c'è niente da togliere e nessuna strada alternativa: prima ricevevi lo stesso errore di sempre, senza capire perché l'aggiornamento non avesse cambiato niente. Ora l'integrazione lo scrive chiaramente.

### 🇬🇧 English

- **A fix to yesterday's feature: on some cars it never kicked in at all.** To decide whether to change route, the integration looked only at the individual function and not at the whole category. On a car whose permission list is shorter — one that does not list the individual functions but denies the group as a whole — it concluded the usual road was open and never tried the alternative: the function stayed broken **on exactly the cars this feature was written for**. It now looks at both.
- **And when nothing can be done, it now says so.** If the manufacturer does not authorise a function on your car at all, there is nothing to remove and no alternative road: you used to get the same error as always, with no way to tell why the update had changed nothing. The integration now says it plainly.

## v1.11.0 — 2026-08-10

### 🇮🇹 Italiano

- **I comandi non si fermano più al primo ostacolo.** Ogni auto ha un elenco, deciso dal costruttore, di ciò che si può comandare a distanza — e cambia da modello a modello. Finora l'integrazione lo ignorava: se anche una sola delle funzioni che un comando porta con sé non era abilitata sulla tua auto, il costruttore rifiutava **tutto il comando**, comprese le parti che la tua auto sapeva fare benissimo. Premevi «Riscalda tutto» e non succedeva niente. Adesso l'integrazione chiede all'auto cosa le è permesso e **toglie dal comando solo i pezzi non abilitati**: il resto parte e funziona. Se qualcosa è stato saltato te lo dice, invece di lasciartelo credere fatto.
- **E se una funzione c'è ma passa da un'altra strada, la usa.** Alcune auto abilitano il riscaldamento dei sedili o lo sbrinamento del lunotto per una via diversa da quella che l'integrazione usava sempre. Prima era un muro: il comando falliva anche se l'auto quella cosa la sapeva fare, e dall'app ufficiale funzionava. Ora, quando la strada abituale è chiusa, l'integrazione prova quella aperta — la stessa che usa l'app. Quando passa di lì si accende anche il clima: te lo scrive, così non è una sorpresa.
- **Se qualcosa non funziona, non ti toglie niente.** Se l'elenco non si riesce a leggere — per esempio perché il servizio del costruttore non risponde — l'integrazione si comporta **esattamente come prima**, mandando il comando per intero. Nessuna funzione sparisce mai per colpa di un problema di rete.
- **Chi ha una Omoda 9 non nota alcuna differenza:** su quell'auto tutto ciò che l'integrazione usa è già abilitato, quindi non c'è niente da togliere e niente da cambiare di strada. Stessi comandi, stessi risultati, stesse entità di prima.
- Grazie a **ThomasMeyer1970** e alla sua Jaecoo 7, da cui è partita tutta questa indagine.

### 🇬🇧 English

- **Commands no longer stop at the first obstacle.** Every car has a list, set by the manufacturer, of what may be controlled remotely — and it differs from model to model. Until now the integration ignored it: if even one of the functions a command carries was not enabled on your car, the manufacturer rejected **the whole command**, including the parts your car could perform perfectly well. You pressed "Heat everything" and nothing happened. The integration now asks the car what it is allowed to do and **removes only the parts that are not enabled**: the rest goes through and works. If something was skipped it tells you, instead of letting you believe it was done.
- **And if a function exists but goes down another road, it takes it.** Some cars enable seat heating or rear-window defrosting through a different route than the one the integration always used. That used to be a dead end: the command failed even though the car could do it, and the official app managed fine. Now, when the usual road is closed, the integration tries the open one — the same the app uses. Going that way also switches the climate on: it tells you, so it is not a surprise.
- **If something goes wrong, nothing is taken away from you.** If the list cannot be read — because the manufacturer's service is not answering, for instance — the integration behaves **exactly as before** and sends the command in full. No function ever disappears because of a network problem.
- **If you have an Omoda 9 you will notice no difference:** on that car everything the integration uses is already enabled, so there is nothing to remove and no road to change. Same commands, same results, same entities as before.
- Thanks to **ThomasMeyer1970** and his Jaecoo 7, where this whole investigation started.

## v1.10.1 — 2026-08-09

### 🇮🇹 Italiano

- **Un messaggio d'errore che mandava fuori strada.** Quando l'auto rifiuta un comando perché il costruttore non ha abilitato quella funzione su quel veicolo, l'integrazione diceva «PIN comandi rifiutato — riconfiguralo nelle impostazioni»: si finiva a reinserire un PIN che era già giusto, senza risolvere niente. Ora dice chiaramente che **non è il PIN** e che quella funzione non è autorizzata su quell'auto. Il messaggio è scritto in italiano e in inglese, così si legge ovunque. Per il resto non cambia nulla: i comandi che funzionavano continuano a funzionare esattamente come prima. Il problema è emerso grazie a **ThomasMeyer1970**, che ha una Jaecoo 7 dove alcuni comandi di comfort non sono abilitati dal costruttore.
- **Il progetto si è trasferito in un'organizzazione condivisa su GitHub.** È cambiato l'indirizzo del progetto: i collegamenti alla documentazione e alla segnalazione dei problemi — quelli che trovi nella scheda dell'integrazione dentro Home Assistant — ora portano al nuovo indirizzo. Da parte tua non c'è niente da fare: l'aggiornamento da HACS continua a funzionare come sempre e la tua configurazione resta intatta.

### 🇬🇧 English

- **An error message that sent you the wrong way.** When the car refuses a command because the manufacturer has not enabled that function on that vehicle, the integration used to say "command PIN rejected — reconfigure it in the settings": you ended up re-entering a PIN that was already correct, and nothing got fixed. It now says clearly that **this is not your PIN** and that the function is not authorised on that car. The message is written in both Italian and English, so it reads anywhere. Nothing else changes: commands that worked keep working exactly as before. The problem came to light thanks to **ThomasMeyer1970**, who has a Jaecoo 7 on which some comfort commands are not enabled by the manufacturer.
- **The project has moved to a shared organisation on GitHub.** The project address has changed: the links to the documentation and to issue reporting — the ones on the integration's page inside Home Assistant — now point to the new address. There is nothing for you to do: updating through HACS keeps working exactly as before and your setup is left untouched.

## v1.10.0 — 2026-08-09

### 🇮🇹 Italiano

- **Ora l'integrazione si adatta alle auto solo elettriche.** Fin qui era tarata sull'Omoda 9, che ha anche il motore a benzina: su un'auto puramente elettrica comparivano lo stesso i contatori del carburante, e restavano vuoti per sempre. Adesso l'integrazione chiede all'auto che tipo di motore ha, e si regola da sola: se è solo elettrica quei contatori non compaiono più, e al loro posto arrivano la **potenza di ricarica**, l'**autonomia dichiarata WLTP** e l'**efficienza**. L'autonomia totale, che sulle ibride è elettrica più benzina, su un'elettrica è semplicemente l'autonomia elettrica.
- **La temperatura del clima usa i limiti veri della tua auto.** Prima il cursore era fisso da 16 a 30 gradi per tutti; ora, quando l'auto li dichiara, si usano i suoi (alcuni modelli hanno estremi diversi, o mezzo grado di scatto invece di uno).
- **La velocità si può vedere in miglia orarie.** Per chi usa Home Assistant con le unità britanniche: prima era bloccata in km/h.
- **Chi ha una Omoda 9 o una Jaecoo ibrida non nota alcuna differenza:** l'adattamento scatta solo quando l'auto dichiara esplicitamente di essere elettrica, mai per esclusione. In caso di dubbio resta tutto com'era.
- Grazie a **JackRonan**, autore della versione inglese dell'integrazione ([omoda-jaecoo-ha](https://github.com/JackRonan/omoda-jaecoo-ha)), che ha portato avanti il lavoro sull'Omoda E5 e da cui arrivano queste migliorie.

### 🇬🇧 English

- **The integration now adapts to fully electric cars.** Until now it was tailored to the Omoda 9, which also has a petrol engine: on a pure EV the fuel gauges showed up anyway and stayed empty forever. The integration now asks the car what kind of engine it has and adjusts by itself: on a fully electric car those gauges are gone, and in their place you get **charging power**, the **official WLTP range** and **efficiency**. Total range, which on a hybrid is electric plus petrol, on an EV is simply the electric range.
- **The climate temperature uses your car's real limits.** The slider used to be fixed at 16 to 30 degrees for everyone; now, when the car declares them, its own limits are used (some models have different ends, or half-degree steps instead of full ones).
- **Speed can be shown in miles per hour.** For anyone running Home Assistant with imperial units: it used to be locked to km/h.
- **If you have an Omoda 9 or a hybrid Jaecoo you will notice no difference:** the adaptation only kicks in when the car explicitly declares itself electric, never by assumption. When in doubt, everything stays as it was.
- Thanks to **JackRonan**, author of the English version of this integration ([omoda-jaecoo-ha](https://github.com/JackRonan/omoda-jaecoo-ha)), who carried the work forward on the Omoda E5 and from whose fork these improvements come.

## v1.9.0 — 2026-08-02

### 🇮🇹 Italiano

- **Ora puoi cambiare come ricevere il codice.** In «Configura» scegli se farti mandare il codice via **email** o via **SMS**, e puoi correggere l'indirizzo o il numero. Prima il canale restava quello scelto alla prima configurazione e l'unico modo di cambiarlo era eliminare e riaggiungere l'integrazione.

### 🇬🇧 English

- **You can now change how you receive the code.** Under "Configure" you choose whether the code is sent by **email** or by **SMS**, and you can correct the address or the number. Before, the channel stayed the one picked at first setup, and the only way to change it was to delete and re-add the integration.

## v1.8.0 — 2026-08-02

### 🇮🇹 Italiano

- **Ora si può accedere con il numero di telefono.** Se il tuo account Omoda/Jaecoo è registrato con un numero invece che con un indirizzo email, scegli «Accedi con numero di telefono»: il codice di verifica ti arriva via **SMS**.

### 🇬🇧 English

- **You can now sign in with your phone number.** If your Omoda/Jaecoo account is registered with a phone number instead of an email address, pick "Sign in with phone number": the verification code arrives by **SMS**.

## v1.7.2 — 2026-08-02

### 🇮🇹 Italiano

- **L'integrazione ha finalmente il suo logo.** Il marchio OMODA | JAECOO compare adesso in HACS e nella pagina delle integrazioni di Home Assistant, al posto del riquadro vuoto. C'è anche la versione chiara per chi usa il tema scuro, così si vede bene in entrambi i casi.

### 🇬🇧 English

- **The integration finally has its own logo.** The OMODA | JAECOO mark now shows up in HACS and on the Home Assistant integrations page, instead of an empty box. A light version is included for anyone on a dark theme, so it reads well either way.

## v1.7.1 — 2026-08-02

### 🇮🇹 Italiano

- **La carica della batteria non torna più indietro da sola.** Appena finita la ricarica l'auto spegne l'impianto elettrico e manda un'ultima lettura "a vuoto": la percentuale che contiene è sbagliata e restava lì per ore. Capitava di vedere 97% in Home Assistant mentre sull'auto c'era 100%. Ora quelle letture vengono riconosciute e scartate.
- **Stessa cosa per l'autonomia.** L'autonomia elettrica non scende più a 0 km, e quella totale non perde di colpo un centinaio di chilometri, quando l'auto è solo a riposo.
- **Quando un dato manca, si tiene l'ultimo vero.** Prima in quei casi poteva ricomparire un valore vecchio, fermo all'ultimo riavvio di Home Assistant: ora si torna sempre all'ultima lettura davvero arrivata dall'auto.
- **«Raffredda tutto» e «Riscalda tutto» partono molto prima.** Se l'auto è già sveglia il comando parte quasi subito, invece di aspettare quasi un minuto come faceva sempre: quell'attesa serviva solo a svegliare un'auto addormentata, e ora si fa soltanto quando serve davvero.
- **Basta l'errore «auto occupata» quando si preme due volte.** Chi non vedeva succedere nulla ripremeva il tasto, i due comandi si accavallavano e l'auto rifiutava il secondo. Ora il secondo comando aspetta sul serio il suo turno.
- **Il messaggio finale dice le cose come stanno.** Quando l'auto avvia il clima ma non i sedili ventilati, ora si legge che il comando è riuscito solo in parte e quali parti hanno fatto storie, invece di un allarme generico seguito da una sfilza di numeri.
- **Niente più falso allarme quando si spegne il clima.** Spegnendo, l'auto manda sempre una nota sul clima che non segnala alcun guasto: veniva scambiata per un problema, così compariva un avviso anche quando tutto era andato benissimo. Ora quella nota, da sola, non fa più scattare nessun allarme.
- **I sedili hanno un nome.** Nel riepilogo di un comando riuscito a metà si legge «sedile guida riscaldato» o «sedile guida ventilato» invece di un anonimo «modulo 4».

### 🇬🇧 English

- **The battery percentage no longer drops back on its own.** Right after charging ends the car shuts down its electrical system and sends one last "empty" reading: the percentage in it is wrong, and it used to stay on screen for hours. You could see 97% in Home Assistant while the car itself showed 100%. Those readings are now recognised and discarded.
- **Same for the range.** The electric range no longer falls to 0 km, and the total range no longer loses a hundred kilometres at once, just because the car is resting.
- **When a reading is missing, the last real one is kept.** Before, an old value could reappear — the one frozen at the last Home Assistant restart. Now it always falls back to the most recent reading actually received from the car.
- **"Cool everything" and "Heat everything" start much sooner.** If the car is already awake the command goes out almost immediately, instead of always waiting nearly a minute: that wait was only there to rouse a sleeping car, and now it happens only when it is actually needed.
- **No more "car busy" error when you press twice.** People who saw nothing happening pressed again, the two commands overlapped and the car rejected the second one. Now the second command really does wait its turn.
- **The final message tells it straight.** When the car starts the climate control but not the ventilated seats, you now read that the command only partly succeeded and which parts refused, instead of a generic alarm followed by a string of numbers.
- **No more false alarm when you switch the climate off.** On every switch-off the car sends a note about the climate control that reports no fault at all: it was being read as a problem, so a warning appeared even when everything had gone perfectly. That note on its own no longer raises any alarm.
- **The seats have names.** In the summary of a partly successful command you now read "driver seat heating" or "driver seat ventilation" instead of an anonymous "module 4".

## v1.7.0 — 2026-07-22

### 🇮🇹 Italiano

- **Basta codici di verifica non richiesti.** Quando il collegamento con l'auto scadeva, l'integrazione spediva un'email col codice da sola — e lo rifaceva a ogni riavvio di Home Assistant. Ora nessun codice parte se non lo chiedi tu.
- **Riautenticazione senza vicoli ciechi.** La pagina ti fa scegliere fra «Inviami un codice nuovo» e «Ho già un codice», e dopo un codice sbagliato ti riporta lì: puoi sempre chiederne un altro.
- **Un avviso quando serve il tuo intervento.** Se il collegamento scade compare una notifica che spiega cosa fare, e sparisce da sola quando tutto torna a posto.
- **Collegamento più stabile.** Si rinnova con ore di anticipo invece che all'ultimo momento, non insiste quando il servizio dell'auto rifiuta, e una connessione ballerina non ti fa più sprecare un codice.
- **Il pulsante «Sveglia auto» torna a funzionare.** In certi casi rispondeva «auto già sveglia» senza fare nulla.
- **Sensori più onesti.** «Dati auto aggiornati» ora segna quando i dati cambiano davvero; «Autonomia combinata» era in realtà l'autonomia a benzina in miglia ed è stata rinominata e corretta; «Tempo di ricarica residuo» torna a "sconosciuto" fuori dalla ricarica.
- **Più riservatezza.** La posizione dell'auto non finisce più nello storico, nel file di diagnostica né nel registro tecnico: continua ad alimentare solo la mappa.

### 🇬🇧 English

- **No more verification codes you didn't ask for.** When the connection to the car expired, the integration emailed a code by itself — and did it again at every Home Assistant restart. Now no code is sent unless you ask for one.
- **Re-authentication without dead ends.** The page lets you choose between "Send me a new code" and "I already have a code", and after a wrong code it takes you back there, so you can always request another.
- **A notification when you need to step in.** If the connection expires, a notification explains what to do, and it disappears on its own once everything is back.
- **A more stable connection.** It renews hours in advance instead of at the last moment, stops insisting when the car service refuses, and a flaky connection no longer makes you waste a code.
- **The "Wake car" button works again.** In some cases it replied "car already awake" and did nothing.
- **More honest sensors.** "Car data updated" now marks when the data really changes; "Combined range" was actually the petrol range in miles and has been renamed and corrected; "Remaining charge time" returns to "unknown" when not charging.
- **More privacy.** The car's location no longer ends up in history, in the diagnostics file or in the technical log: it only feeds the map.

## v1.6.1 — 2026-07-20

### 🇮🇹 Italiano

- **Avvio più pulito e spegnimento più rapido di Home Assistant.** All'avvio
  l'integrazione si caricava e, subito dopo, si ricaricava una seconda volta da sola:
  succedeva mentre andava a recuperare il nome della tua auto. Un lavoro inutile, che in
  più poteva **rallentare lo spegnimento o il riavvio di Home Assistant** se capitava
  nel momento sbagliato. Ora l'integrazione si ricarica **solo quando serve davvero**,
  cioè quando cambi tu le impostazioni.
- Anche cambiando il PIN dei comandi l'integrazione si ricaricava due volte di fila:
  ora una sola. Non cambia nulla in ciò che vedi, è tutto più ordinato e veloce.
- **Corretto un difetto negli strumenti interni di diagnostica**, quelli che chi sviluppa
  l'integrazione può accendere per indagare un problema segnalato. In certi casi il file
  che producono poteva contenere la **posizione dell'auto** invece di ometterla come
  previsto. Quegli strumenti restano spenti a meno che non vengano attivati apposta,
  quindi con ogni probabilità non ti ha mai riguardato — ma se ti fosse mai stato chiesto
  di inviare un file di diagnostica, da questa versione è di nuovo oscurato come promesso.

### 🇬🇧 English

- **Cleaner startup and faster Home Assistant shutdown.** At startup the integration
  loaded and then immediately reloaded itself a second time, while fetching your car's
  name. That was wasted work, and it could also **slow down Home Assistant's shutdown or
  restart** if it happened at the wrong moment. The integration now reloads **only when
  it actually needs to**, that is when you change the settings yourself.
- Changing the command PIN also caused two reloads in a row: now just one. Nothing
  changes in what you see, it is simply tidier and faster.
- **Fixed a defect in the internal diagnostic tooling** — the tooling the integration's
  developer can switch on to investigate a reported problem. In some cases the file it
  produces could contain the **car's location** instead of omitting it as intended. That
  tooling stays switched off unless deliberately enabled, so in all likelihood this never
  affected you — but if you were ever asked to send a diagnostic file, from this version
  it is properly redacted again, as promised.

## v1.6.0 — 2026-07-20

### 🇮🇹 Italiano

- **Grande lavoro di riordino interno: non cambia nulla in ciò che vedi e usi.** Nessuna
  funzione nuova, nessun pulsante spostato, nessuna entità in più o in meno. Cambia il
  modo in cui l'integrazione è scritta sotto il cofano.
- **Perché l'abbiamo fatto.** Alcuni problemi seri visti nei mesi scorsi — il PIN che si
  bloccava da solo, gli aggiornamenti automatici che continuavano a interrogare l'auto
  anche da spenti, il messaggio d'errore sbagliato che ti mandava a cambiare un PIN in
  realtà corretto — erano stati sistemati uno per uno. Ora abbiamo cambiato le fondamenta
  perché quel genere di problema **non possa più ripresentarsi**, invece di correggerlo
  ogni volta che salta fuori.
- **La novità più importante non si vede.** L'integrazione ha ora una batteria di **184
  controlli automatici** che verificano da soli, in pochi secondi, che tutto funzioni:
  comandi, accesso, telemetria, avvisi e persino il conteggio esatto delle 105 entità.
  Prima l'unico modo di provare una modifica era **provarla sull'auto vera**. Da oggi non
  serve più: le modifiche future arrivano già verificate.
- **Preparato il supporto a più auto sullo stesso Home Assistant.** Non è ancora attivo,
  ma l'ostacolo tecnico che lo impediva è stato rimosso.
- **Un po' più di riservatezza.** Il PIN e l'indirizzo email non transitano più in una
  zona di memoria che altre integrazioni installate potevano leggere.
- **Puoi aggiornare tranquillamente:** il comportamento è identico a prima.

### 🇬🇧 English

- **Major internal clean-up: nothing changes in what you see and use.** No new features,
  no buttons moved, no entities added or removed. What changed is how the integration is
  written under the hood.
- **Why we did it.** Some serious problems seen in recent months — the PIN locking itself
  out, automatic updates that kept polling the car even when switched off, the wrong error
  message sending you to change a PIN that was actually correct — had been fixed one by
  one. We have now changed the foundations so that this *kind* of problem **can no longer
  happen at all**, rather than fixing it each time it appears.
- **The most important change is invisible.** The integration now has a battery of **184
  automated checks** that verify on their own, in a few seconds, that everything works:
  commands, sign-in, telemetry, warnings, even the exact count of the 105 entities.
  Previously the only way to test a change was **to try it on the real car**. That is no
  longer needed: future changes arrive already verified.
- **Groundwork for multiple cars on the same Home Assistant.** Not enabled yet, but the
  technical obstacle that prevented it has been removed.
- **A little more privacy.** Your PIN and email address no longer pass through an area of
  memory that other installed integrations could read.
- **You can update safely:** behaviour is identical to before.

## v1.5.29 — 2026-07-19

### 🇮🇹 Italiano

- **Aggiornamento di manutenzione: per te non cambia nulla.** Nessuna nuova funzione e nessuna
  correzione visibile: solo una rifinitura agli strumenti interni di chi sviluppa l'integrazione.
  Restano spenti e non influiscono sul funzionamento: puoi aggiornare tranquillamente.

### 🇬🇧 English

- **Maintenance update: nothing changes for you.** No new features and no visible fixes — just a
  refinement to the integration developer's internal tooling. It stays switched off and does not
  affect how anything works: you can update safely.

## v1.5.28 — 2026-07-19

### 🇮🇹 Italiano

- **Aggiornamento di manutenzione: per te non cambia nulla.** Non ci sono nuove funzioni né
  correzioni visibili. Questa versione aggiunge solo strumenti interni che aiutano chi sviluppa
  l'integrazione a capire meglio i problemi segnalati. Restano spenti e non influiscono in alcun
  modo sul funzionamento né sui consumi: puoi aggiornare tranquillamente.

### 🇬🇧 English

- **Maintenance update: nothing changes for you.** No new features and no visible fixes. This
  release only adds internal tooling that helps the integration's developer investigate reported
  problems. It stays switched off and has no effect whatsoever on behaviour or resource usage —
  you can update safely.

## v1.5.27 — 2026-07-19

### 🇮🇹 Italiano

- **Non ti chiede più di rifare l'accesso quando è solo internet che fa i capricci.** Se il
  collegamento con il server dell'auto cadeva per un attimo, poteva comparire la richiesta di
  rientrare con un nuovo codice via email — inutile, perché la sessione era ancora buona. Ora
  l'integrazione distingue "sessione davvero scaduta" da "problema di rete passeggero" e ti
  disturba solo quando serve per davvero.
- **Un accesso in meno da rifare a mano.** In alcuni casi la sessione poteva essere rinnovata da
  sola, in silenzio, ma l'integrazione non ci provava e ti chiedeva subito il codice via email.
  Ora tenta prima il rinnovo automatico: spesso non dovrai fare nulla.
- **Basta con il falso "PIN sbagliato".** Quando l'auto rifiutava un comando per motivi che col
  PIN non c'entrano nulla (per esempio l'account non ha i permessi su quella vettura), ti veniva
  comunque detto che il PIN era errato e ti veniva chiesto di cambiarlo. Peggio: quel rifiuto
  veniva contato come tentativo sbagliato e ti avvicinava al blocco del PIN. Ora ogni rifiuto
  viene riconosciuto per quello che è: il messaggio dice la causa vera, il PIN corretto non viene
  più messo in discussione e non si consumano tentativi per colpa di errori che non sono tuoi.
- **Il PIN non si vede più in chiaro.** Nelle schermate per cambiare il PIN dei comandi, il codice
  appariva scritto per esteso. Ora è mascherato con i pallini, come una normale password.
- **Il codice via email è più al riparo.** Email e codice di verifica non vengono più passati in un
  modo che, su alcuni sistemi, poteva renderli visibili ad altri programmi in esecuzione. Inoltre,
  quando spegni o rimuovi l'integrazione, PIN ed email non restano più in memoria.
- **Il file di diagnostica non rivela più dove tieni i certificati.** Se lo invii per farti aiutare,
  ora il percorso della cartella (che spesso contiene il tuo nome utente) viene oscurato come già
  accadeva per email, targa e posizione.
- **Il nome del sensore "Dati auto aggiornati" ora è tradotto** anche in italiano e in inglese,
  come tutti gli altri.
- **Per chi ci aiuta a trovare i problemi:** ora è possibile chiedere a Home Assistant i log
  dettagliati dell'integrazione dalla sua pagina, senza smanettare nei file di configurazione.

### 🇬🇧 English

- **No more "please sign in again" when it's just the internet acting up.** If the connection to
  the car's server dropped for a moment, you could be asked to sign in again with a new email
  code — pointless, since the session was still fine. The integration now tells a genuinely
  expired session apart from a passing network glitch, and only bothers you when it really matters.
- **One less sign-in to do by hand.** In some cases the session could have been renewed silently on
  its own, but the integration didn't try and asked you for the email code straight away. It now
  attempts the automatic renewal first: often you won't have to do anything.
- **No more false "wrong PIN".** When the car refused a command for reasons that have nothing to do
  with the PIN (for example, the account lacks permissions on that vehicle), you were still told
  the PIN was wrong and asked to change it. Worse, that refusal counted as a failed attempt and
  pushed you closer to having your PIN locked. Every refusal is now recognised for what it is: the
  message states the real cause, a correct PIN is no longer questioned, and attempts are no longer
  used up because of errors that aren't yours.
- **Your PIN is no longer shown in plain text.** On the screens for changing the command PIN, the
  code was displayed in full. It is now masked with dots, like any normal password.
- **The email code is better protected.** Your email address and verification code are no longer
  passed in a way that, on some systems, could make them visible to other running programs. Also,
  when you shut down or remove the integration, the PIN and email no longer linger in memory.
- **The diagnostics file no longer reveals where you keep your certificates.** If you send it in to
  get help, the folder path (which often contains your username) is now hidden, just as your email,
  VIN and location already were.
- **The "Car data updated" sensor name is now translated** into both Italian and English, like all
  the others.
- **For those helping us track down problems:** you can now ask Home Assistant for the integration's
  detailed logs from its own page, without editing configuration files by hand.

## v1.5.26 — 2026-07-19

### 🇮🇹 Italiano

- **Meno rischio di bloccare il PIN dell'auto.** Se due richieste partivano nello stesso momento
  (per esempio premi "Sveglia" due volte, o un comando mentre l'auto si sta svegliando), potevano
  provare il codice di sicurezza in parallelo e "consumare" più tentativi del previsto: con un PIN
  sbagliato si rischiava di avvicinarsi al blocco dell'account. Ora le richieste si mettono in fila
  e viene rispettato il limite di tentativi che l'integrazione si è data.
- **Reinserire lo stesso PIN ora sblocca davvero.** Se dopo un errore riconfermavi il PIN identico
  a prima (perché in realtà il problema non era il PIN), il blocco di sicurezza restava attivo e i
  comandi continuavano a non partire per diversi minuti. Ora, ogni volta che confermi il PIN
  — dall'avviso di riparazione o dalle impostazioni — si riparte puliti.
- **Se la sveglia dell'auto fallisce, ora te lo dice.** Quando il tentativo di risveglio non
  riusciva per PIN o sessione scaduta, l'errore restava nascosto nei log: nessun avviso, nessuna
  richiesta di reinserire il codice. Ora compare l'avviso giusto, esattamente come quando premi un
  pulsante: correggi il PIN o rifai l'accesso e riprovi.
- **Niente più letture in sottofondo dopo aver spento l'integrazione.** Se ricaricavi o rimuovevi
  l'integrazione mentre l'auto era in carica, un controllo automatico poteva restare acceso e
  continuare a interrogare il server anche dopo. Ora si ferma insieme a tutto il resto.
- **L'interruttore "Aggiornamento automatico" ora ferma tutto.** Spegnendolo mentre l'auto era
  sotto carica, il controllo ravvicinato della ricarica proseguiva lo stesso. Ora quando è spento
  l'integrazione non contatta più l'auto da sola, come ci si aspetta.

### 🇬🇧 English

- **Less risk of locking your car's PIN.** If two requests started at the same moment (for example
  pressing "Wake" twice, or sending a command while the car is waking up), they could try the
  security code in parallel and burn more attempts than intended — with a wrong PIN that meant
  getting closer to an account lockout. Requests are now queued and the attempt limit the
  integration sets for itself is properly respected.
- **Re-entering the same PIN now really unblocks it.** If after an error you confirmed the very
  same PIN (because the problem wasn't the PIN after all), the safety block stayed active and
  commands kept failing for several minutes. Now every time you confirm the PIN — from the repair
  notice or from the settings — it starts fresh.
- **If waking the car fails, you're now told.** When the wake-up attempt failed because of the PIN
  or an expired session, the error stayed hidden in the logs: no notice, no request to re-enter the
  code. Now you get the proper notice, exactly as when you press a button: fix the PIN or sign in
  again, then retry.
- **No more background readings after switching the integration off.** If you reloaded or removed
  the integration while the car was charging, an automatic check could stay alive and keep querying
  the server afterwards. It now stops together with everything else.
- **The "Automatic update" switch now stops everything.** Turning it off while the car was charging
  did not stop the close-interval charge tracking. Now, when it is off, the integration no longer
  contacts the car on its own — as you would expect.

## v1.5.25 — 2026-07-11

### 🇮🇹 Italiano

- **Comandi più veloci.** Prima ogni comando rifaceva da capo la verifica del PIN col server: ora
  l'autorizzazione ottenuta viene riusata per una decina di minuti, quindi la maggior parte dei
  comandi parte subito. Se l'auto la rifiuta perché scaduta, l'integrazione la rinnova e riprova
  da sola, senza mostrarti un errore.
- **Niente più "un altro comando è in corso".** L'auto esegue un comando alla volta: prima, se ne
  premevi un secondo mentre il primo era in volo, veniva rifiutato con un errore. Ora **si mette in
  coda** e parte da solo appena l'auto ha confermato il precedente.
- **Sicurezza e riservatezza.** Tre correzioni: l'integrazione non scrive più su disco i dati grezzi
  dell'auto (che contenevano telaio e posizione GPS); il file di diagnostica che puoi condividere per
  chiedere aiuto **non contiene più il numero di telaio**; i file con le credenziali di accesso sono
  ora leggibili solo dal proprietario.
- **Configurazione iniziale: correggere l'email adesso funziona.** Se sbagliavi a digitare l'email,
  ogni nuovo tentativo continuava a usare quella vecchia e falliva finché non riavviavi Home
  Assistant. Ora ogni tentativo usa l'email che hai appena scritto. In più, se il codice non parte,
  ora **vedi scritto il motivo** sotto al modulo (prima non appariva da nessuna parte).
- **Basta codice vecchio dopo un aggiornamento.** In certi casi, dopo un update, Home Assistant
  continuava a far girare la versione precedente di alcune parti interne. Ora vengono ricaricate
  sempre da zero: aggiornare e riavviare basta.
- **Tolto un doppione tra gli indicatori del motore.** C'erano due voci per lo stato del motore
  ("Motore" e "Motore acceso") che mostravano la stessa identica informazione: ne resta una sola
  ("Motore"), quella storica. Nessuna funzione persa, solo un po' di ordine in più.
- **Diagnosi più precisa quando un comando viene rifiutato per il PIN.** Quando l'auto non accetta
  il codice di sicurezza dei comandi, ora l'integrazione **mostra e registra il codice esatto**
  restituito dal server. Serve a distinguere con certezza un vero "PIN sbagliato" da altre cause
  (permessi del veicolo, problema temporaneo del server): utile se, dopo aver corretto il PIN, i
  comandi continuassero a non partire.

### 🇬🇧 English

- **Faster commands.** Every command used to redo the full PIN check with the server: the
  authorisation is now reused for about ten minutes, so most commands go straight through. If the
  car rejects it as expired, the integration renews it and retries on its own, without showing you
  an error.
- **No more "another command is still in progress".** The car runs one command at a time: before, a
  second press while the first was in flight was rejected with an error. Now it **waits its turn**
  and runs as soon as the car has confirmed the previous one.
- **Security and privacy.** Three fixes: the integration no longer writes the raw vehicle data to
  disk (it contained the VIN and the GPS position); the diagnostics file you can share when asking
  for help **no longer contains the VIN**; the files holding your access credentials are now
  readable by their owner only.
- **Setup: correcting your email now works.** If you mistyped your email, every retry kept using the
  old one and failed until you restarted Home Assistant. Each attempt now uses the email you just
  typed. Also, when the code can't be sent, **the reason is now shown** under the form (previously
  it appeared nowhere).
- **No more old code running after an update.** In some cases, after an update, Home Assistant kept
  running the previous version of some internal parts. They are now always reloaded from scratch:
  updating and restarting is enough.
- **Removed a duplicate engine indicator.** There were two entries for the engine state ("Engine"
  and "Engine running") showing the exact same information: only one remains ("Engine"), the
  original. No functionality lost, just a bit tidier.
- **More precise diagnosis when a command is rejected because of the PIN.** When the car doesn't
  accept the command security code, the integration now **shows and logs the exact code** returned
  by the server. This tells a genuine "wrong PIN" apart from other causes (vehicle permissions, a
  temporary server issue): useful if commands still won't go through after you've corrected the PIN.

### 🙏 Grazie / Credits

Le migliorie di questa versione (velocità dei comandi, coda, correzioni di sicurezza e privacy,
setup, ricarica del codice dopo un update) nascono dal lavoro di **[JackRonan](https://github.com/JackRonan)**
nel suo fork inglese [omoda-jaecoo-ha](https://github.com/JackRonan/omoda-jaecoo-ha), da cui sono
state riportate qui. Grazie di cuore per averle trovate, risolte e condivise. — *The improvements in
this release (command speed, queueing, security and privacy fixes, setup, code reloading after an
update) come from **JackRonan**'s work on his English fork, and were ported back here. Thank you!*

## v1.5.24 — 2026-07-06

### 🇮🇹 Italiano

- **Risolto il problema più insidioso: comandi che sembravano riusciti ma l'auto non faceva
  nulla.** Se il **PIN a 4 cifre dei comandi remoti** è sbagliato, l'auto rifiuta ogni comando:
  finora però l'interruttore in Home Assistant restava sul "fatto" e sembrava tutto a posto
  (mentre finestrini, clima, serratura ecc. non si muovevano). Ora, in questo caso, **l'interruttore
  torna subito allo stato reale** e compare un chiaro messaggio: **«PIN comandi errato»**.
- **Puoi correggere il PIN senza dover eliminare e riaggiungere l'integrazione.** Compare un avviso
  di **riparazione** di Home Assistant (Impostazioni → il classico avviso in alto) che, con un clic,
  ti fa **inserire il PIN corretto** e sistema tutto da solo. In alternativa trovi la stessa cosa in
  **Impostazioni → Dispositivi e servizi → Omoda 9 → Riconfigura**. Non serve alcun codice via email:
  il PIN dei comandi non c'entra con l'accesso. (Consiglio: non insistere con un PIN errato, per non
  rischiare il blocco dell'account.)
- **Se l'accesso scade (capita se apri l'app ufficiale sul telefono) ora te lo dice chiaramente.**
  Prima l'unico modo per rimettere a posto la sessione era cercare dei pulsanti "nascosti"; ora
  Home Assistant mostra l'avviso standard **«Ri-autenticazione necessaria»**: premi, ricevi un
  **codice via email** e lo inserisci — e i dati tornano. I vecchi pulsanti OTP restano comunque
  disponibili come riserva.

### 🇬🇧 English

- **Fixed the nastiest problem: commands that looked successful while the car did nothing.** If the
  **4-digit remote-command PIN** is wrong, the car rejects every command — but until now the switch
  in Home Assistant stayed on "done" and everything looked fine (while windows, climate, lock, etc.
  didn't move). Now, in this case, **the switch snaps back to its real state** and a clear message
  appears: **"Wrong command PIN"**.
- **You can fix the PIN without deleting and re-adding the integration.** A Home Assistant **repair**
  notice appears (Settings → the usual banner at the top) that, with one click, lets you **enter the
  correct PIN** and sorts everything out. Alternatively you'll find the same under **Settings →
  Devices & services → Omoda 9 → Reconfigure**. No email code is needed: the command PIN has nothing
  to do with logging in. (Tip: don't keep retrying with a wrong PIN, to avoid locking the account.)
- **If your session expires (which happens if you open the official phone app) it now tells you
  clearly.** Previously the only way to restore the session was to hunt for "hidden" buttons; now
  Home Assistant shows the standard **"Re-authentication required"** notice: click it, get a **code
  by email**, enter it — and the data comes back. The old OTP buttons remain available as a fallback.

## v1.5.23 — 2026-07-06

### 🇮🇹 Italiano

- **Batteria e chilometri restano aggiornati anche ad auto ferma, e la macchina viene "svegliata"
  molto meno di prima.** Abbiamo scoperto che l'auto resta raggiungibile dal cloud per ore dopo
  averla usata: in questa finestra l'integrazione legge batteria, chilometri, autonomia e gomme
  **in sola lettura, senza svegliarla**. Quindi ora la sveglia (che consuma un pochino la batteria
  da 12V e può dare fastidio all'app ufficiale sul telefono) parte **solo quando serve davvero**,
  cioè quando l'auto è effettivamente "addormentata"; se è già raggiungibile, i dati si aggiornano
  da soli senza alcun risveglio. È stato aggiunto anche un nuovo indicatore **"Dati auto
  aggiornati"** che mostra a che ora risale l'ultimo dato ricevuto dall'auto, così sai quanto è
  fresco quello che vedi. Migliorato infine il riconoscimento della marcia (in certi casi l'auto
  risultava ferma pur essendo in movimento). Tutto rigorosamente **a sola lettura**.
- **Gli interruttori non mostrano più un finto "fatto" quando l'auto rifiuta il comando.** Se
  invii un comando (chiudi, clima, serratura…) mentre l'auto sta già eseguendo qualcos'altro, è
  occupata e non lo esegue: prima l'interruttore restava acceso come se fosse andato a buon fine
  e bisognava aspettare diversi secondi per riprovare. Ora l'interruttore **torna subito allo
  stato reale**, compare un avviso chiaro («auto occupata, riprova tra qualche secondo») e puoi
  **ritentare immediatamente**. Lo stesso vale per gli altri rifiuti dell'auto (funzione non
  consentita su questa vettura, sessione da rifare): niente più falsi "eseguito".
- **Nuovi indicatori e autonomia totale più realistica.** Aggiunti quattro nuovi indicatori
  verificati dal vivo: **Motore acceso**, **Alta tensione attiva**, **Avviso carburante basso**
  e **Avviso ricarica necessaria**. In cambio abbiamo tolto alcuni indicatori che questa vettura
  non trasmette proprio (restavano per sempre "sconosciuto" e non facevano che confondere:
  temperatura abitacolo, alcuni contachilometri parziali, potenza di ricarica, velocità media,
  consumo istantaneo, tempi di ricarica rapida). Infine l'**Autonomia totale** ora è calcolata
  come **elettrica + benzina** (prima usava un valore del cruscotto che, verificato sul campo,
  restava fisso e non seguiva la carica) → il numero mostrato è finalmente coerente con lo stato
  reale di batteria e serbatoio.

### 🇬🇧 English

- **Battery and mileage stay fresh even while the car is parked, and the car is "woken up" far less
  than before.** We found that the car stays reachable from the cloud for hours after you use it:
  during that window the integration reads battery, mileage, range and tyres **read-only, without
  waking it**. So the wake-up (which slightly uses the 12V battery and can interfere with the
  official phone app) now happens **only when actually needed** — i.e. when the car is genuinely
  asleep; if it's already reachable, the data refreshes on its own with no wake-up at all. We also
  added a new **"Car data updated"** indicator showing the time of the last data received from the
  car, so you know how fresh what you see is. Driving detection was also improved (in some cases the
  car looked stationary while actually moving). Everything strictly **read-only**.
- **Switches no longer show a fake "done" when the car rejects the command.** If you send a
  command (close, climate, lock…) while the car is already doing something else, it's busy and
  won't run it: previously the switch stayed on as if it had succeeded, and you had to wait
  several seconds before retrying. Now the switch **snaps back to its real state**, a clear notice
  appears ("car busy, try again in a few seconds") and you can **retry right away**. The same
  applies to the car's other rejections (feature not allowed on this vehicle, session needs
  re-login): no more false "executed".
- **New indicators and a more realistic total range.** Added four new live-verified indicators:
  **Engine running**, **High voltage active**, **Low fuel warning** and **Charge needed warning**.
  In exchange we removed a few indicators this vehicle simply doesn't transmit (they stayed
  "unknown" forever and only caused confusion: cabin temperature, some trip odometers, charging
  power, average speed, instant consumption, fast-charge times). Finally, **Total range** is now
  computed as **electric + petrol** (it previously used a dashboard value that, verified in the
  field, stayed fixed and didn't follow the charge) → the number shown is finally consistent with
  the real battery and tank state.

## v1.5.22 — 2026-06-24

### 🇮🇹 Italiano

- **Ora i dati dell'auto si aggiornano da soli mentre guidi.** Prima, durante un viaggio, valori
  come batteria, chilometri percorsi e autonomia restavano fermi finché non premevi a mano il
  pulsante "Aggiorna stato completo": l'auto in movimento, infatti, non invia aggiornamenti
  spontanei. Adesso l'integrazione se ne accorge da sola e, mentre sei in marcia, aggiorna i dati
  da sola circa ogni minuto, senza che tu debba toccare niente. A vettura ferma o in ricarica non
  cambia nulla rispetto a prima. Tutto questo avviene **solo a lettura**: non viene inviato alcun
  comando all'auto e non si consuma la batteria. Funziona con l'interruttore "Aggiornamento
  automatico" acceso (come già era).

### 🇬🇧 English

- **Your car's data now updates by itself while you drive.** Until now, during a trip, values like
  battery, distance travelled and range stayed frozen until you manually pressed the "Refresh full
  status" button: a moving car doesn't send updates on its own. Now the integration notices this by
  itself and, while you're driving, refreshes the data roughly every minute with no action from you.
  When the car is parked or charging nothing changes compared to before. This is **read-only**: no
  command is ever sent to the car and it doesn't drain the battery. It works with the "Automatic
  update" switch turned on (as it already was).

## v1.5.21 — 2026-06-23

### 🇮🇹 Italiano

- **Risolto: non si riusciva più ad aggiungere l'integrazione (errore "not_implemented").**
  Chi installava l'integrazione da zero, alla voce **Aggiungi integrazione → Omoda 9 / Jaecoo**,
  riceveva subito un errore "not_implemented" e non riusciva a inserire email e PIN. La schermata
  di accesso non veniva proposta per niente. Ora la procedura di configurazione (email → codice
  ricevuto via mail → eventuale scelta dell'auto) funziona di nuovo correttamente. Chi aveva già
  configurato l'integrazione in precedenza non era interessato dal problema.

### 🇬🇧 English

- **Fixed: the integration could no longer be added (error "not_implemented").**
  Anyone installing the integration from scratch, under **Add integration → Omoda 9 / Jaecoo**,
  immediately got a "not_implemented" error and couldn't enter their email and PIN. The login
  screen wasn't shown at all. The setup process (email → code received by mail → optional vehicle
  selection) now works correctly again. Anyone who had already configured the integration was not
  affected by this problem.

## v1.5.20 — 2026-06-23

- **Nomi delle entità in italiano o inglese, in automatico secondo la lingua di Home
  Assistant.** Finora i nomi delle entità (Batteria, Autonomia, Porte…) erano sempre in
  italiano. Ora ogni entità è **tradotta**: chi usa Home Assistant in inglese vede "Battery",
  "Total range", "Front left door"…, chi lo usa in italiano vede "Batteria", "Autonomia
  totale", "Porta anteriore SX". Il nome del veicolo fa da prefisso (es. **"Omoda 9 Battery"**,
  o **"Jaecoo 7 Battery"** per chi ha un Jaecoo). `entity_id`, storico, automazioni e dashboard
  **non cambiano**. (Se avevi rinominato a mano qualche entità, il tuo nome personalizzato
  resta e ha la precedenza.)

## v1.5.19 — 2026-06-23

- **Il dispositivo prende il nome reale della tua auto (Omoda 9, Jaecoo 7…).** Prima il
  dispositivo si chiamava sempre "Omoda 9", anche per chi ha un Jaecoo. Ora il nome (e
  marca/modello) vengono **rilevati automaticamente dall'auto** — è lo stesso nome che vedi
  nell'app. Se preferisci, puoi cambiarlo a mano in **Impostazioni → Dispositivi e servizi →
  Omoda 9 / Jaecoo → Configura → "Nome veicolo"**. Gli `entity_id`, lo storico, le automazioni
  e le dashboard **non cambiano** (il dispositivo è identificato dal numero di telaio).

## v1.5.18 — 2026-06-23

- **Il sensore "Connessa" si chiama ora "Connessione".** È sempre lo stesso sensore (uno
  solo, con stato **Connesso/Disconnesso**): il nome neutro si legge meglio quando l'auto
  è offline. Niente di tecnico cambia e i riferimenti esistenti restano validi.

## v1.5.17 — 2026-06-23

- **"Autonomia totale" corretta + nuovo dato "Autonomia benzina".** Il valore che
  l'integrazione chiamava "Autonomia totale" (215 km) in realtà era **solo l'autonomia
  a benzina**, non la somma con l'elettrico: lo si è verificato perché restava fermo a
  215 km mentre l'autonomia elettrica calava (e il serbatoio era invariato). Ora:
  **"Autonomia benzina"** mostra i km col solo motore termico, e **"Autonomia totale"**
  mostra il valore corretto = **elettrico + benzina** (es. 27 + 215 = 242 km).
- **Pressione gomme in bar (come nell'app).** Le quattro pressioni degli pneumatici ora
  sono mostrate in **bar** invece che in kPa (es. 2,79 bar invece di 279 kPa), così
  coincidono con quanto vedi nell'app dell'auto. Potresti vedere una notifica una-tantum
  di "unità cambiata": si risolve da sola, lo storico viene convertito automaticamente.

## v1.5.16 — 2026-06-23

- **L'aggiornamento automatico della ricarica ora parte subito anche dopo un riavvio
  di Home Assistant.** Nella versione precedente, se riavviavi Home Assistant mentre
  l'auto era già in carica, il monitoraggio in tempo reale poteva non avviarsi da solo
  finché non scattava il controllo periodico (anche mezz'ora dopo) — perché l'auto, da
  ferma, non "annuncia" nulla. Ora, **pochi secondi dopo l'avvio**, l'integrazione fa
  una lettura: se trova l'auto in carica (o in marcia) **fa partire immediatamente**
  l'aggiornamento ogni paio di minuti. Sempre in sola lettura, nessun comando all'auto.

## v1.5.15 — 2026-06-23

- **Piccola regolazione del controllo periodico durante la ricarica (ogni 30 minuti
  invece di 39).** È solo una rete di sicurezza: a seguire la carica in tempo reale
  ci pensa già l'aggiornamento automatico ogni paio di minuti introdotto qui sopra.
  Nessun cambiamento visibile nell'uso di tutti i giorni.

## v1.5.14 — 2026-06-23

- **La carica si segue da sola: mentre l'auto è attaccata alla colonnina, batteria,
  tempo che manca alla fine e potenza di ricarica si aggiornano automaticamente.**
  Prima, anche durante la ricarica i dati potevano restare "fermi" all'ultimo valore
  per ore (l'auto non li manda da sola): bisognava premere "Aggiorna stato completo"
  per vederli. Ora, **appena colleghi il cavo, l'integrazione inizia a rileggere i
  dati di carica ogni paio di minuti** e li tiene aggiornati per tutta la durata della
  ricarica — vedi la percentuale che sale e il tempo residuo che scende senza fare
  nulla. Quando stacchi il cavo, smette da sola. Tutto in sola lettura: **nessun
  comando viene inviato all'auto** (durante la carica i dati veri sono già disponibili).

## v1.5.13 — 2026-06-23

- **I chilometri e la batteria ora si aggiornano da soli quando guidi.** Era
  emerso che l'odometro restava "fermo" all'ultimo valore e la batteria sembrava
  bloccata. Il motivo: l'auto comunica i dati **veri** (chilometri totali, carica
  della batteria, tensione) **solo quando l'alta tensione è accesa** — cioè mentre
  la guidi o la ricarichi. A macchina parcheggiata e spenta non c'è nessun dato
  nuovo da leggere (vale anche per l'app ufficiale). Ora, **appena l'auto si
  accende o va in carica, l'integrazione legge i dati freschi più volte di
  seguito**, così i chilometri salgono e la batteria si aggiorna **automaticamente
  durante e dopo ogni viaggio**, senza che tu debba fare nulla.
- **Nuovo pulsante "Aggiorna stato completo".** Se vuoi vedere subito i
  chilometri e la batteria aggiornati mentre l'auto è parcheggiata, premilo:
  accende il **clima per circa un minuto** (è l'unico modo per "risvegliare"
  l'alta tensione), legge i dati reali e poi **rispegne il clima da solo**. Da
  usare solo quando ti serve il dato fresco al volo: nell'uso normale non serve,
  perché ora si aggiorna da sé quando guidi.
- **Niente più "batteria 0%" fuorviante.** Se l'integrazione non ha ancora mai
  letto una carica reale, mostra **"sconosciuto"** invece di un falso 0% — finché
  non arriva il primo dato vero (al primo viaggio/ricarica o col pulsante qui
  sopra).

## v1.5.12 — 2026-06-22

- **La batteria non va più a 0 quando l'auto è parcheggiata.** Quando l'auto è
  ferma e spenta non comunica la carica reale della batteria (manda uno "zero"
  segnaposto): prima questo faceva apparire la **batteria allo 0%** e la
  **tensione/corrente** dell'alta tensione azzerate. Ora l'integrazione riconosce
  questi valori finti e **mantiene l'ultimo valore reale** — esattamente come fa
  l'app ufficiale, che mostra sempre l'ultima carica nota. I valori "veri" di
  batteria, tensione, corrente e consumo elettrico tornano ad aggiornarsi da soli
  quando l'auto è **in marcia o in ricarica** (gli unici momenti in cui l'auto li
  trasmette davvero).

## v1.5.11 — 2026-06-22

- **Login e avvio più robusti.** Migliorata la stabilità in alcune situazioni
  poco comuni: se il server dell'auto risponde in modo inatteso durante l'invio
  del codice OTP o la verifica del captcha, ora l'integrazione **riprova invece
  di bloccarsi**. All'avvio, se qualcosa va storto, **non lascia più processi o
  controlli automatici "appesi"** in sottofondo, e durante lo spegnimento fa
  pulizia in modo più ordinato. Il file con le credenziali dell'auto viene salvato
  in modo **a prova di interruzione** (non può più corrompersi se Home Assistant
  si chiude proprio in quel momento). Infine, quando spegni l'interruttore
  **"Aggiornamento automatico"**, l'aggiornamento periodico si ferma **davvero**,
  senza più riattivarsi da solo. Sono tutti miglioramenti "dietro le quinte": l'uso
  di tutti i giorni non cambia.

## v1.5.10 — 2026-06-22

- **Più facile chiedere aiuto se qualcosa non va.** Aggiunto il pulsante **"Scarica
  diagnostica"** nella pagina dell'integrazione (menù ⋮): con un clic scarichi un file da
  inviare per farti aiutare, **già reso anonimo** — la tua email, il PIN, il numero di
  telaio e soprattutto la **posizione dell'auto** sono nascosti automaticamente, e di
  password e certificati non viene mai mostrato il contenuto. Nel manuale (README) trovi ora
  una sezione **"Risoluzione problemi"** che spiega in parole semplici dove trovare i log e
  come inviarli in sicurezza.

## v1.5.9 — 2026-06-22

- **"Raffredda tutto" e "Riscalda tutto" ora si spengono davvero del tutto (sedili
  posteriori inclusi).** Per spegnere tutto usa lo stesso pulsante **"Raffredda tutto"**
  (o "Riscalda tutto") e mettilo su **OFF**: così spegni aria + **tutti** i sedili, anche
  quelli posteriori. ⚠️ Attenzione: il pulsante **"Clima"** spegne solo l'aria condizionata
  (e, sull'auto, i sedili anteriori che le sono collegati), ma **non** i sedili posteriori —
  quelli sono indipendenti. Inoltre l'interruttore ora **resta acceso** mentre il preset è
  attivo (prima si rispegneva subito e non riuscivi a comandarne lo spegnimento), e **si
  spegne da solo** dopo circa 15 minuti, quando l'auto chiude il preset. Anche lo spegnimento
  sveglia l'auto da solo, così arriva fino ai sedili posteriori.

## v1.5.8 — 2026-06-22

- **"Raffredda tutto" e "Riscalda tutto": basta un tocco, anche con l'auto parcheggiata.**
  I sedili, il volante e gli sbrinatori l'auto li accende solo quando è **sveglia**: se la
  premevi a vettura ferma da un po', l'auto era "addormentata" e rispondeva con un errore.
  Ora la macro **sveglia l'auto da sola e aspetta qualche secondo** prima di mandare il
  comando, quindi ti basta premere una volta e funziona (ci mette ~40 secondi a partire:
  è normale, sta svegliando l'auto). Inoltre il pulsante ora fa **sempre l'accensione**
  quando lo premi: prima, se era rimasto "acceso", il tocco mandava per sbaglio lo
  spegnimento (che dava errore). 💡 Per il momento miglior risultato, usalo con l'**auto
  spenta**.

## v1.5.7 — 2026-06-22

- **"Raffredda tutto" e "Riscalda tutto" ora accendono DAVVERO tutto** (e si corregge
  quanto detto nelle due note precedenti). Le macro tornano a fare ciò che ti aspetti, con
  un unico comando come l'app ufficiale:
  - **❄️ Raffredda tutto** = aria condizionata al massimo freddo **+ ventilazione di tutti
    e quattro i sedili**.
  - **🔥 Riscalda tutto** = aria calda al massimo **+ riscaldamento di tutti e quattro i
    sedili + volante riscaldato + sbrinatore parabrezza + sbrinatore lunotto**.

  Perché prima sembravano "non disponibili": i comandi del comfort (sedili, volante,
  sbrinatori) l'auto li accetta **solo a vettura spenta e con il clima acceso**. Se l'auto
  è accesa/occupata, o se si prova ad accendere un sedile col clima spento, l'auto li
  rifiuta con un errore — e questo mi aveva tratto in inganno facendomi credere, a torto,
  che certi comfort non fossero installati. Verificato dal vivo a motore spento: clima,
  tutti i sedili, volante, parabrezza e lunotto rispondono correttamente. **Consiglio
  d'uso:** lancia "Raffredda/Riscalda tutto" con l'**auto spenta**.

## v1.5.6 — 2026-06-21

- **"Raffredda tutto" e "Riscalda tutto" ora sono vere macro su misura per la tua auto.**
  Abbiamo provato sul campo, uno per uno, tutti i comfort dell'auto per vedere quali
  rispondono davvero ai comandi a distanza. Su questa vettura risultano installati (e
  funzionanti) soltanto il **sedile guidatore ventilato** e lo **sbrinatore del lunotto**;
  riscaldamento dei sedili, volante riscaldato, sbrinatore del parabrezza e ventilazione
  dei sedili passeggero/posteriori **non sono presenti** e andavano solo in errore. Quindi
  adesso:
  - **❄️ Raffredda tutto** = aria condizionata al massimo freddo **+ ventilazione del
    sedile guidatore**.
  - **🔥 Riscalda tutto** = aria calda al massimo **+ sbrinatore del lunotto**.

  I comandi vengono inviati **in sequenza, uno alla volta** (l'auto ne esegue uno per
  volta), quindi la macro impiega qualche secondo in più a completarsi ma non si "accavalla"
  e non genera più gli errori che vedevi. Niente più tentativi sui comfort che la tua auto
  non ha.

## v1.5.5 — 2026-06-21

- **"Raffredda tutto" e "Riscalda tutto" ora funzionano davvero.** Prima questi due
  pulsanti usavano un comando "tutto-in-uno" che la tua auto non riesce a eseguire: dava un
  finto "comando inviato" e subito dopo un errore, e il clima non partiva. Ora usano il
  comando del climatizzatore semplice (lo stesso, affidabile, del termostato "Clima"):
  **"Raffredda tutto"** accende l'aria al massimo freddo, **"Riscalda tutto"** al massimo
  caldo (e accende anche gli sbrinatori di parabrezza e lunotto). Il riscaldamento/la
  ventilazione dei **sedili** non fanno più parte di questi due pulsanti — l'auto non li
  accettava in quel comando — ma restano comandabili dai loro interruttori dedicati.

## v1.5.4 — 2026-06-21

- **Niente più comandi accavallati se premi troppe volte.** L'auto esegue **un comando
  alla volta**: ora, finché un comando è in corso, le pressioni successive vengono
  ignorate con un avviso ("attendi qualche secondo, un comando è già in corso") invece di
  accavallarsi e farsi rifiutare dall'auto come "occupato". Appena l'auto conferma, il
  comando successivo riparte subito. Vale per tutti i comandi che **agiscono** sull'auto
  (clima, serrature, baule/finestrini/tetto, ricarica, sedili, antifurto, "Raffredda/
  Riscalda tutto").

## v1.5.3 — 2026-06-21

- **L'aggiornamento automatico ora parte SPENTO.** Per non svegliare l'auto senza che tu
  lo voglia, la funzione "Aggiornamento automatico" è **disattivata di default**: quando la
  vuoi, accendi tu l'interruttore **"Aggiornamento automatico"** (e regoli gli intervalli
  dalle opzioni). Resta valido il pulsante "Aggiorna posizione" per un aggiornamento manuale.

## v1.5.2 — 2026-06-21

- **Aggiornamento automatico dei dati dell'auto.** Ora Home Assistant aggiorna **da solo**,
  a intervalli regolari, le informazioni dell'auto (posizione, batteria, autonomia, gomme,
  consumi…) svegliando brevemente la vettura. Di **default ogni 60 minuti**, e **ogni 39
  minuti quando l'auto è attaccata alla colonnina** (così segui meglio la ricarica).
  - Puoi cambiare i due intervalli — o disattivarli mettendo **0** — dalle opzioni
    dell'integrazione: **Impostazioni → Dispositivi e servizi → Omoda 9 → Configura**.
  - C'è anche un nuovo interruttore **"Aggiornamento automatico"** per accendere o spegnere
    tutto con un tocco, senza entrare nelle opzioni.
  - ⚠️ Quando è attivo l'auto viene svegliata periodicamente: comodo per avere dati sempre
    freschi, ma comporta un piccolo consumo della batteria a vettura ferma. Se preferisci,
    spegnilo e aggiorna a mano col pulsante "Aggiorna posizione".

- **Stati della ricarica più chiari.** Le informazioni "Stato ricarica", "Presa ricarica
  rapida" e "Ricarica programmata" ora mostrano un **testo leggibile** (es. "Non in ricarica",
  "In ricarica", "Collegata") invece di un codice numerico.

## v1.5.1 — 2026-06-21

- **Correzione: le nuove informazioni dall'auto ora compaiono davvero.** Per un problema
  tecnico, i dati che l'auto comunica quando è sveglia — autonomia, chilometri, pressione e
  temperatura delle gomme, consumi, carburante, tensione della batteria, e perfino **livello
  batteria e velocità** — non venivano letti e restavano vuoti. Ora vengono letti
  correttamente: i relativi sensori si popolano non appena l'auto si sveglia.

- **Avviso quando un comando all'auto non riesce (opzionale).** Ora è disponibile un
  "blueprint" pronto all'uso: se lo importi, ricevi un **popup in Home Assistant** (e, se
  vuoi, una notifica sul telefono) ogni volta che un comando all'auto non va a buon fine —
  ad esempio quando l'auto è occupata da un altro comando, non è raggiungibile, o la
  sessione è scaduta. Riconosce solo i veri errori, quindi non disturba quando va tutto
  bene. L'integrazione di suo continua a **non inviare nessuna notifica**: il blueprint è
  del tutto facoltativo e si attiva con un clic dal README.

## v1.5.0 — 2026-06-21

- **Tante nuove informazioni che arrivano direttamente dall'auto.** Quando l'auto è
  sveglia, Home Assistant ora mostra molti più dati utili, finora non disponibili:
  - **Autonomia**: quanti chilometri restano in elettrico e in totale (elettrico + benzina).
  - **Chilometri totali** dell'auto (contachilometri) e chilometri percorsi in ibrido.
  - **Gomme**: pressione e temperatura di ognuna delle quattro ruote, con un **avviso**
    dedicato per ciascuna gomma se qualcosa non va.
  - **Consumi medi**, sia di benzina sia di energia elettrica.
  - **Carburante rimasto** nel serbatoio (in litri).
  - **Batteria di trazione**: tensione e corrente (informazioni tecniche).
  - **Clima**: la temperatura impostata sui due lati dell'abitacolo.
  - **Ricarica**: stato della presa, stato della ricarica programmata e, quando l'auto è
    in carica, il tempo che manca al termine.
  - **Avviso "batteria scarica"** quando il livello è basso.

  Sono tutte informazioni di **sola lettura** (l'auto non riceve nessun comando) e si
  aggiornano quando l'auto si sveglia. Le trovi sotto il dispositivo "Omoda 9": quelle
  più tecniche (temperature gomme, tensione batteria, ecc.) sono raggruppate tra i
  "dettagli diagnostici".

## v1.4.0 — 2026-06-21

- **Nuovo interruttore "Antifurto".** Puoi accendere e spegnere l'allarme antifurto
  dell'auto direttamente da Home Assistant. Quando è acceso, l'auto fa scattare l'allarme
  e ti avvisa in caso di movimento non autorizzato del veicolo, tentativi di scasso delle
  porte, rottura dei finestrini o altre potenziali effrazioni. L'interruttore mostra anche
  se l'antifurto è già attivo (lo legge dall'auto).
- **Due nuovi tasti "comfort": Raffredda tutto e Riscalda tutto.** Con un solo
  interruttore prepari l'abitacolo per la stagione. **"Raffredda tutto"** accende il
  clima al massimo del freddo e avvia la **ventilazione di tutti i sedili**.
  **"Riscalda tutto"** accende il clima al massimo del caldo e attiva insieme lo
  **sbrinamento di parabrezza e lunotto, il volante riscaldato e il riscaldamento di
  tutti i sedili**. I due tasti si escludono a vicenda: accendendone uno, l'altro si
  spegne. Comodi per scaldare o rinfrescare l'auto in un colpo solo prima di partire.
- **Ricarica programmata: ora scegli l'orario al minuto.** L'ora di inizio della
  ricarica programmata era un cursore a sole ore intere (es. solo "le 8"); adesso c'è un
  vero **selettore d'orario** "Ricarica · orario di inizio" con cui imposti anche i minuti
  (es. **07:45**). La durata resta il cursore in ore. ⚠️ Dopo l'aggiornamento il vecchio
  cursore "Ricarica · ora di inizio" resterà "non disponibile" e si può togliere: al suo
  posto usa il nuovo selettore d'orario.

## v1.3.0 — 2026-06-21

- **Il clima ora si imposta alla temperatura che vuoi.** Prima c'era un semplice
  interruttore che accendeva il clima fisso a 21°; ora trovi un vero **termostato**:
  scegli la temperatura desiderata (da 16° a 30°) e l'auto la applica, riscaldando o
  raffreddando l'abitacolo. Puoi anche regolare per quanti minuti deve restare acceso.
  ⚠️ Dopo l'aggiornamento, al posto del vecchio interruttore "Clima" comparirà il nuovo
  termostato "Clima": se avevi messo il vecchio interruttore in una schermata, sostituiscilo
  con il nuovo (il vecchio resterà "non disponibile" e si può togliere).
- **Comandi per la ricarica elettrica.** Due nuovi interruttori: **"Ricarica"** per
  avviare o fermare subito la ricarica, e **"Ricarica programmata"** per far caricare
  l'auto in una fascia oraria scelta (imposti ora di inizio e durata con i due cursori
  dedicati). Funzionano quando l'auto è collegata alla colonnina/wallbox.
- **I sedili e gli sbrinamenti non si toccano più accendendo il clima.** Il nuovo
  termostato agisce solo sull'aria: riscaldamento sedili, volante e sbrinamenti restano
  controlli a parte e non vengono spenti quando accendi o spegni il clima.

## v1.2.0 — 2026-06-21

- **Comandi anche per i sedili passeggero e posteriori.** Finora potevi accendere e
  spegnere solo il sedile del posto guida; ora trovi gli stessi interruttori (caldo e
  aria) anche per il **passeggero** e per i due **sedili posteriori** (sinistro e
  destro). Come per il guida, su ogni sedile caldo e aria si escludono a vicenda.
- **Nuove informazioni dall'auto.** Compaiono tre nuove indicazioni quando l'auto è
  sveglia: se la **spina di ricarica è collegata**, se il **motore è acceso**, e lo
  stato di movimento del **tetto apribile** (quest'ultimo tra i dettagli tecnici).
- **L'esito dei comandi ora arriva davvero dall'auto.** Prima la voce "Esito comando"
  diceva solo che il comando era stato *accettato* dal server; adesso, quando l'auto
  risponde, viene aggiornata con l'esito **reale**: comando eseguito e confermato,
  ancora in corso, oppure non riuscito (con il motivo segnalato dall'auto).

- **Riscaldamenti e sbrinamenti ora si spengono con un tocco.** Sbrinamento
  parabrezza, sbrinamento lunotto, volante riscaldato e i sedili (caldo/aria) del
  posto guida diventano dei normali interruttori: prima potevi solo accenderli (e si
  spegnevano da soli dopo 15 minuti), ora li accendi **e li spegni** quando vuoi,
  vedendo lo stato acceso/spento nella stessa card.
- **Sedile guida più furbo.** Caldo e aria del sedile guida non possono stare accesi
  insieme: accendendo l'aria il riscaldamento si spegne (e viceversa), proprio come
  fa l'auto — e ora la card lo mostra subito.
- **Tasto "Sveglia auto" più affidabile.** Se la sveglia via SMS non risponde
  (capitava che l'auto restasse a riposo), l'integrazione prova in automatico a
  contattare l'auto con la richiesta di posizione, che la sveglia al primo colpo e
  in più aggiorna la posizione GPS.
- **Schermata più pulita.** Un paio di indicazioni che l'auto non comunica mai da
  ferma (tendina del tetto, riscaldamento parabrezza) sono state spostate tra i
  dettagli diagnostici, così non restano "in dubbio" tra i controlli principali.

## v1.0.0 — 2026-06-21

- **Versione 1.0: l'integrazione diventa stabile e più affidabile.** Tante piccole
  rifiniture sotto il cofano per un funzionamento più solido di tutti i giorni.
- **Connessione all'auto più robusta.** Se il collegamento cade viene ristabilito
  da solo, senza lasciare l'integrazione "appesa"; meno disconnessioni inattese e
  un avvio più pulito quando l'auto non è raggiungibile.
- **Accesso più sicuro e protetto.** Migliorata la gestione dell'accesso per evitare
  che la sessione si perda da sola; aggiunta una protezione che ferma i tentativi se
  il PIN risulta sbagliato, così l'account non rischia il blocco.
- **Informazioni sempre veritiere dopo un riavvio.** Dopo aver riavviato Home
  Assistant, gli esiti dei comandi non mostrano più un risultato vecchio: o è
  aggiornato o resta vuoto, niente informazioni fuorvianti.
- **Stati più coerenti.** Porte, serratura, baule, finestrini, tetto e clima
  vengono interpretati in modo uniforme: niente più "acceso" o "aperto" mostrati
  per sbaglio quando il dato non c'è.
- **Comandi con conferma a schermo.** Quando premi un comando (chiudi/apri/clima)
  la card si aggiorna subito e, se qualcosa non va a buon fine, te lo segnala invece
  di restare bloccata su uno stato mai raggiunto.
- **Pronta anche fuori dall'Europa.** In fase di configurazione si può ora indicare
  il server dell'auto della propria zona, così l'integrazione funziona anche fuori
  dalla regione europea.
- **La posizione GPS resta salvata.** L'ultima posizione nota viene conservata e
  ricompare dopo un riavvio, invece di sparire.

## v0.3.0 — 2026-06-21

- **La serratura ora è un vero lucchetto.** La blocchi e la sblocchi con un solo
  tocco, e vedi lo stato (chiusa/aperta) nella stessa card. Prima erano
  un'indicazione separata e due pulsanti distinti.
- **Il clima ora è un interruttore.** Lo accendi e lo spegni come una normale luce
  (l'accensione avvia la climatizzazione a 21° per 15 minuti).
- **Baule, finestrini e tetto si comandano come tapparelle.** Apri e chiudi
  direttamente, con stato e comando insieme. (La ventilazione finestrini resta un
  pulsante a parte.)
- **Schermata principale più pulita.** Le informazioni di servizio — esiti dei
  comandi, orari dell'ultimo contatto, stato della sessione e campo del codice OTP —
  sono state spostate nella sezione "diagnostica" del dispositivo, così in primo
  piano restano solo i controlli che usi davvero.
- **Andamenti nel tempo per batteria e velocità.** Ora vengono registrate
  storicamente: puoi vederne i grafici e usarle nelle statistiche.

## v0.2.6 — 2026-06-21

- Aggiunto questo elenco delle novità (changelog), così a ogni aggiornamento
  vedi in chiaro cosa è cambiato.
- README più chiaro: per iniziare bastano **email + PIN** del tuo account
  (più un **codice OTP** via email al primo accesso). Tutto il resto è automatico.

## v0.2.4 — 21 giugno 2026

- **Certificati automatici.** Non devi più procurarti o inserire alcun
  certificato: l'integrazione li installa da sola in base alla tua regione.
  L'attivazione richiede ora soltanto email e PIN.

## v0.2.1 — 21 giugno 2026

- **Accesso più semplice.** Ora puoi accedere direttamente da Home Assistant
  inserendo email e PIN e confermando il codice OTP ricevuto via email, senza
  strumenti esterni e su qualunque installazione (anche Home Assistant OS).

## Versioni precedenti

- Prime versioni dell'integrazione: collegamento dell'auto a Home Assistant
  (stato porte/serrature/baule/cofano/finestrini/tetto/clima/sedili), posizione
  GPS su richiesta, batteria e velocità ad auto in marcia, pulsanti dei comandi.
