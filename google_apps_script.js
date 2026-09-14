/**
 * Google Apps Script - Webhook API untuk Sistem Presensi Mahasiswa & Kelas
 * Sinkronisasi dua arah SQLite <-> Google Sheets.
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
        result[name] = sheet ? getSheetData(sheet) : [];
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
    if (!e || !e.postData || !e.postData.contents) {
      return jsonResponse({ status: "error", message: "Body POST kosong." });
    }

    var postData = JSON.parse(e.postData.contents);
    var action = postData.action;

    if (action === "sync_all") {
      var tables = postData.tables || {};
      for (var tableName in tables) {
        writeFullTable(ss, tableName, tables[tableName]);
      }
      return jsonResponse({ status: "success", message: "Semua tabel berhasil disinkronkan ke Google Sheets." });
    }

    if (action === "upsert_row") {
      var tableName = postData.table;
      var keyField = postData.key || "id";
      var rowData = postData.row || {};
      if (!tableName || Object.keys(rowData).length === 0) {
        return jsonResponse({ status: "error", message: "Table atau row tidak valid." });
      }
      var sheet = getOrCreateSheet(ss, tableName);
      upsertRowInSheet(sheet, keyField, rowData);
      return jsonResponse({ status: "success", message: "Baris berhasil di-upsert di sheet " + tableName });
    }

    if (action === "append_row") {
      var tableName = postData.table;
      var rowData = postData.row || {};
      var sheet = getOrCreateSheet(ss, tableName);
      appendRowToSheet(sheet, rowData);
      return jsonResponse({ status: "success", message: "Baris baru berhasil ditambahkan di sheet " + tableName });
    }

    if (action === "delete_row") {
      var tableName = postData.table;
      var keyField = postData.key || "id";
      var keyValue = postData.value;
      var sheet = ss.getSheetByName(tableName);
      if (sheet) deleteRowInSheet(sheet, keyField, keyValue);
      return jsonResponse({ status: "success", message: "Baris berhasil dihapus dari sheet " + tableName });
    }

    return jsonResponse({ status: "error", message: "Action POST tidak dikenal: " + action });
  } catch (err) {
    return jsonResponse({ status: "error", message: err.toString() });
  }
}

function getSheetData(sheet) {
  var data = sheet.getDataRange().getValues();
  if (data.length === 0) return [];

  // Sheet baru/kosong kadang tetap menghasilkan satu sel kosong.
  if (data.length === 1 && data[0].length === 1 && String(data[0][0]).trim() === "") return [];
  if (data.length <= 1) return [];

  var headers = data[0];
  var rows = [];
  for (var i = 1; i < data.length; i++) {
    var rowObj = {};
    var hasValue = false;
    for (var j = 0; j < headers.length; j++) {
      if (!headers[j]) continue;
      var val = data[i][j];
      if (val !== "" && val !== null) hasValue = true;
      if (val instanceof Date) {
        val = Utilities.formatDate(val, "Asia/Jakarta", "yyyy-MM-dd HH:mm:ss");
      }
      rowObj[String(headers[j])] = val;
    }
    if (hasValue) rows.push(rowObj);
  }
  return rows;
}

function getOrCreateSheet(ss, name) {
  var sheet = ss.getSheetByName(name);
  return sheet || ss.insertSheet(name);
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
  formatHeader(sheet, headers.length);
}

function ensureHeaders(sheet, rowData) {
  var range = sheet.getDataRange();
  var values = range.getValues();

  // Spreadsheet kosong: buat header berdasarkan field row yang dikirim.
  if (values.length === 1 && values[0].length === 1 && String(values[0][0]).trim() === "") {
    var headers = Object.keys(rowData);
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    formatHeader(sheet, headers.length);
    return headers;
  }

  return values[0];
}

function formatHeader(sheet, count) {
  if (count > 0) {
    sheet.getRange(1, 1, 1, count)
      .setFontWeight("bold")
      .setBackground("#1E40AF")
      .setFontColor("#FFFFFF");
  }
}

function appendRowToSheet(sheet, rowData) {
  var headers = ensureHeaders(sheet, rowData);
  var newRow = [];
  for (var j = 0; j < headers.length; j++) {
    var val = rowData[headers[j]];
    newRow.push(val !== undefined && val !== null ? String(val) : "");
  }
  sheet.appendRow(newRow);
}

function upsertRowInSheet(sheet, keyField, rowData) {
  var data = sheet.getDataRange().getValues();
  var emptySheet = data.length === 1 && data[0].length === 1 && String(data[0][0]).trim() === "";
  if (emptySheet) {
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
      rowIndex = i + 1;
      break;
    }
  }

  if (rowIndex > 0) {
    var updatedRow = [];
    for (var j = 0; j < headers.length; j++) {
      var val = rowData[headers[j]];
      updatedRow.push(val === undefined || val === null ? data[rowIndex - 1][j] : String(val));
    }
    sheet.getRange(rowIndex, 1, 1, headers.length).setValues([updatedRow]);
  } else {
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
