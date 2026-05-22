/**
 * Point d'enregistrement effectif des composants preview dans le `registry`.
 *
 * Chaque mock importé ici doit appeler `registerPreview(nodeId, Component, …)`
 * lors de son chargement (idéalement via un side-effect en haut du fichier).
 *
 * Les pages V1 (Dashboard, Offers, Homepage, Page projet) et les modules
 * isolés sont enregistrés ci-dessous. Les nodes non listés retombent sur
 * `<NotImplementedPlaceholder>` à la consommation.
 */

import './pages/registerDashboard'
import './pages/registerOffers'
import './pages/registerHomepage'
import './pages/registerProjet'
import './modules/registerModules'
