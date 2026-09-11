/**
 * Google Apps Script - Webhook API untuk Sistem Presensi Mahasiswa & Kelas
 * 
 * CARA MEMASANG DI GOOGLE SHEETS:
 * 1. Buat Google Spreadsheet baru (atau Import file migrasi_data_presensi_google_sheets.xlsx).
 * 2. Klik menu: Ekstensi (Extensions) > Apps Script.
 * 3. Hapus semua kode default, lalu tempel (paste) seluruh isi file ini.
 * 4. Klik ikon Simpan (Disk) di atas.
 * 5. Klik tombol biru "Terapkan" (Deploy) > "Penerapan baru" (New deployment).
 * 6. Pilih jenis: "Aplikasi Web" (Web app).
 * 7. Setel:
 *    - Deskripsi: API Presensi Lab
 *    - Jalankan sebagai: Saya (email Anda)
 *    - Siapa yang memiliki akses: Siapa saja (Anyone)
 * 8. Klik "Terapkan" (Deploy) dan izinkan akses akun Google Anda.
 * 9. Salin (Copy) "URL Aplikasi Web" (contoh: https://script.google.com/macros/s/.../exec).
 * 10. Tempelkan URL tersebut ke Pengaturan Aplikasi Presensi atau secrets.toml!
 */

function doGet(e) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var params = e ? e.parameter : {};
    var action = params.action || "get_all";
    
    if (action === "ping") {
      return jsonResponse({ status: "success", message: "Google Apps Script Presensi aktif!", title: ss.getName() });
    }
    
    if (action === "get_all") {
      var result = {};
      var sheetNames = ["mahasiswa", "presensi", "riwayat_kelas", "riwayat_izin", "riwayat_tugas_luar"];
      
      sheetNames.forEach(function(name) {
        var sheet = ss.getSheetByName(name);
        if (sheet) {
          result[name] = getSheetData(sheet);
        } else {
          result[name] = [];
        }
      });
      
      return jsonResponse({ status: "success", data: result });
    }
    
    if (action === "get_table") {
      var tableName = params.table;
      var sheet = ss.getSheetByName(tableName);
      if (!sheet) {
        return jsonResponse({ status: "error", message: "Sheet " + tableName + " tidak ditemukan" });
      }
      return jsonResponse({ status: "success", data: getSheetData(sheet) });
    }
    
    return jsonResponse({ status: "error", message: "Action tidak dikenal: " + action });
  } catch (err) {
    return jsonResponse({ status: "error", message: err.toString() });
  }
}

function doPost(e) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var postData = JSON.parse(e.postData.contents);
    var action = postData.action;

    // 1. Sinkronisasi seluruh tabel sekaligus (Migrasi Awal)
    if (action === "sync_all") {
      var tables = postData.tables || {};
      for (var tableName in tables) {
        var rows = tables[tableName];
        writeFullTable(ss, tableName, rows);
      }
      return jsonResponse({ status: "success", message: "Semua tabel berhasil disinkronkan ke Google Sheets." });
    }

    // 2. Tambah / Perbarui baris (Upsert)
    if (action === "upsert_row") {
      var tableName = postData.table;
      var keyField = postData.key || "id";
      var rowData = postData.row;
      var sheet = getOrCreateSheet(ss, tableName);

      upsertRowInSheet(sheet, keyField, rowData);
      return jsonResponse({ status: "success", message: "Baris berhasil di-upsert di sheet " + tableName });
    }

    // 3. Tambah baris baru saja (Append)
    if (action === "append_row") {
      var tableName = postData.table;
      var rowData = postData.row;
      var sheet = getOrCreateSheet(ss, tableName);

      appendRowToSheet(sheet, rowData);
      return jsonResponse({ status: "success", message: "Baris baru berhasil ditambahkan di sheet " + tableName });
    }

    // 4. Hapus baris berdasarkan key
    if (action === "delete_row") {
      var tableName = postData.table;
      var keyField = postData.key || "id";
      var keyValue = postData.value;
      var sheet = ss.getSheetByName(tableName);

      if (sheet) {
        deleteRowInSheet(sheet, keyField, keyValue);
      }
      return jsonResponse({ status: "success", message: "Baris berhasil dihapus dari sheet " + tableName });
    }

    return jsonResponse({ status: "error", message: "Action POST tidak dikenal: " + action });
  } catch (err) {
    return jsonResponse({ status: "error", message: err.toString() });
  }
}

// ================= FUNGSI BANTU =================

function getSheetData(sheet) {
  var data = sheet.getDataRange().getValues();
  if (data.length <= 1) return [];
  var headers = data[0];
  var rows = [];

  for (var i = 1; i < data.length; i++) {
    var rowObj = {};
    for (var j = 0; j < headers.length; j++) {
      var val = data[i][j];
      if (val instanceof Date) {
        val = Utilities.formatDate(val, "Asia/Jakarta", "yyyy-MM-dd HH:mm:ss");
      }
      rowObj[headers[j]] = val;
    }
    rows.push(rowObj);
  }
  return rows;
}

function getOrCreateSheet(ss, name) {
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}

function writeFullTable(ss, name, rows) {
  var sheet = getOrCreateSheet(ss, name);
  sheet.clear();
  if (!rows || rows.length === 0) return;

  var headers = Object.keys(rows[0]);
  var allData = [headers];

  for (var i = 0; i < rows.length; i++) {
    var r = [];
    for (var j = 0; j < headers.length; j++) {
      var val = rows[i][headers[j]];
      r.push(val !== undefined && val !== null ? String(val) : "");
    }
    allData.push(r);
  }

  sheet.getRange(1, 1, allData.length, headers.length).setValues(allData);
  sheet.getRange(1, 1, 1, headers.length).setFontWeight("bold").setBackground("#1E40AF").setFontColor("#FFFFFF");
}

function appendRowToSheet(sheet, rowData) {
  var dataRange = sheet.getDataRange();
  var headers = dataRange.getValues()[0];
  if (!headers || headers.length === 0) {
    headers = Object.keys(rowData);
    sheet.appendRow(headers);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight("bold").setBackground("#1E40AF").setFontColor("#FFFFFF");
  }

  var newRow = [];
  for (var j = 0; j < headers.length; j++) {
    var val = rowData[headers[j]];
    newRow.push(val !== undefined && val !== null ? String(val) : "");
  }
  sheet.appendRow(newRow);
}

function upsertRowInSheet(sheet, keyField, rowData) {
  var data = sheet.getDataRange().getValues();
  if (data.length <= 1) {
    appendRowToSheet(sheet, rowData);
    return;
  }

  var headers = data[0];
  var keyIdx = headers.indexOf(keyField);
  if (keyIdx === -1) {
    appendRowToSheet(sheet, rowData);
    return;
  }

  var targetVal = String(rowData[keyField]);
  var rowIndex = -1;

  for (var i = 1; i < data.length; i++) {
    if (String(data[i][keyIdx]) === targetVal) {
      rowIndex = i + 1; // 1-indexed for Sheet row
      break;
    }
  }

  if (rowIndex > 0) {
    // Update baris
    var updatedRow = [];
    for (var j = 0; j < headers.length; j++) {
      var val = rowData[headers[j]];
      if (val === undefined || val === null) {
        updatedRow.push(data[rowIndex - 1][j]); // pertahankan nilai lama jika tidak disediakan
      } else {
        updatedRow.push(String(val));
      }
    }
    sheet.getRange(rowIndex, 1, 1, headers.length).setValues([updatedRow]);
  } else {
    // Tambah baru
    appendRowToSheet(sheet, rowData);
  }
}

function deleteRowInSheet(sheet, keyField, keyValue) {
  var data = sheet.getDataRange().getValues();
  if (data.length <= 1) return;
  var headers = data[0];
  var keyIdx = headers.indexOf(keyField);
  if (keyIdx === -1) return;

  var targetVal = String(keyValue);
  for (var i = data.length - 1; i >= 1; i--) {
    if (String(data[i][keyIdx]) === targetVal) {
      sheet.deleteRow(i + 1);
      break;
    }
  }
}

function jsonResponse(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
