<?php
// Laragon Web Server Redirect
// Aplikasi Python (Flask) berjalan di port 5050 secara mandiri.
// File ini akan otomatis mengalihkan (redirect) pengunjung pantauin.test ke http://localhost:5050
header("Location: http://localhost:5050/");
exit();
?>
