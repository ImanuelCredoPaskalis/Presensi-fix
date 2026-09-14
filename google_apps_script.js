/**
 * Google Apps Script - Webhook API untuk Sistem Presensi Mahasiswa & Kelas
 * Sinkronisasi dua arah SQLite <-> Google Sheets.
 */

function doGet(e) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var params = e ? e.parameter : {};
    var action = params.action || "get_all";
    if (action === "ping") return jsonResponse({status:"success", message:"Google Apps Script Presensi aktif!", title:ss.getName()});
    if (action === "get_all") {
      var result = {};
      ["mahasiswa","presensi","riwayat_kelas","riwayat_izin","riwayat_tugas_luar"].forEach(function(name) {
        var sheet = ss.getSheetByName(name);
        result[name] = sheet ? getSheetData(sheet) : [];
      });
      return jsonResponse({status:"success", data:result});
    }
    if (action === "get_table") {
      var sheet = ss.getSheetByName(params.table);
      if (!sheet) return jsonResponse({status:"error", message:"Sheet " + params.table + " tidak ditemukan"});
      return jsonResponse({status:"success", data:getSheetData(sheet)});
    }
    return jsonResponse({status:"error", message:"Action tidak dikenal: " + action});
  } catch (err) { return jsonResponse({status:"error", message:err.toString()}); }
}

function doPost(e) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    if (!e || !e.postData || !e.postData.contents) return jsonResponse({status:"error", message:"Body POST kosong."});
    var postData = JSON.parse(e.postData.contents);
    var action = postData.action;

    if (action === "sync_all") {
      var tables = postData.tables || {};
      for (var tableName in tables) writeFullTable(ss, tableName, tables[tableName]);
      return jsonResponse({status:"success", message:"Semua tabel berhasil disinkronkan ke Google Sheets."});
    }

    if (action === "upsert_row") {
      var tableName = postData.table;
      var keyField = postData.key || "id";
      var rowData = postData.row || {};
      if (!tableName || Object.keys(rowData).length === 0) return jsonResponse({status:"error", message:"Table atau row tidak valid."});
      upsertRowInSheet(getOrCreateSheet(ss, tableName), keyField, rowData);
      return jsonResponse({status:"success", message:"Baris berhasil di-upsert di sheet " + tableName});
    }

    if (action === "append_row") {
      var tableName = postData.table;
      var rowData = postData.row || {};
      appendRowToSheet(getOrCreateSheet(ss, tableName), rowData);
      return jsonResponse({status:"success", message:"Baris berhasil ditambahkan."});
    }

    if (action === "delete_row") {
      var sheet = ss.getSheetByName(postData.table);
      if (sheet) deleteRowInSheet(sheet, postData.key || "id", postData.value);
      return jsonResponse({status:"success", message:"Baris berhasil dihapus."});
    }
    return jsonResponse({status:"error", message:"Action POST tidak dikenal: " + action});
  } catch (err) { return jsonResponse({status:"error", message:err.toString()}); }
}

function getSheetData(sheet) {
  var data = sheet.getDataRange().getValues();
  if (data.length === 0 || (data.length === 1 && data[0].length === 1 && String(data[0][0]).trim() === "")) return [];
  if (data.length <= 1) return [];
  var headers = data[0], rows = [];
  for (var i=1; i<data.length; i++) {
    var rowObj = {}, hasValue = false;
    for (var j=0; j<headers.length; j++) {
      if (!headers[j]) continue;
      var val = data[i][j];
      if (val !== "" && val !== null) hasValue = true;
      if (val instanceof Date) val = Utilities.formatDate(val, "Asia/Jakarta", "yyyy-MM-dd HH:mm:ss");
      rowObj[String(headers[j])] = val;
    }
    if (hasValue) rows.push(rowObj);
  }
  return rows;
}

function getOrCreateSheet(ss, name) { return ss.getSheetByName(name) || ss.insertSheet(name); }

function writeFullTable(ss, name, rows) {
  var sheet = getOrCreateSheet(ss, name);
  sheet.clear();
  if (!rows || rows.length === 0) return;
  var headers = Object.keys(rows[0]), allData = [headers];
  for (var i=0; i<rows.length; i++) {
    var r=[];
    for (var j=0; j<headers.length; j++) r.push(rows[i][headers[j]] !== undefined && rows[i][headers[j]] !== null ? String(rows[i][headers[j]]) : "");
    allData.push(r);
  }
  sheet.getRange(1,1,allData.length,headers.length).setValues(allData);
  formatHeader(sheet, headers.length);
}

function ensureHeaders(sheet, rowData) {
  var values = sheet.getDataRange().getValues();
  if (values.length === 1 && values[0].length === 1 && String(values[0][0]).trim() === "") {
    var headers = Object.keys(rowData);
    sheet.getRange(1,1,1,headers.length).setValues([headers]);
    formatHeader(sheet, headers.length);
    return headers;
  }

  var headers = values[0].map(function(h){ return String(h || "").trim(); });
  var changed = false;
  Object.keys(rowData).forEach(function(key) {
    if (headers.indexOf(key) === -1) {
      headers.push(key);
      changed = true;
    }
  });
  if (changed) {
    sheet.getRange(1,1,1,headers.length).setValues([headers]);
    formatHeader(sheet, headers.length);
  }
  return headers;
}

function formatHeader(sheet, count) {
  if (count > 0) sheet.getRange(1,1,1,count).setFontWeight("bold").setBackground("#1E40AF").setFontColor("#FFFFFF");
}

function appendRowToSheet(sheet, rowData) {
  var headers = ensureHeaders(sheet, rowData), newRow=[];
  for (var j=0; j<headers.length; j++) newRow.push(rowData[headers[j]] !== undefined && rowData[headers[j]] !== null ? String(rowData[headers[j]]) : "");
  sheet.appendRow(newRow);
}

function upsertRowInSheet(sheet, keyField, rowData) {
  var data = sheet.getDataRange().getValues();
  var empty = data.length === 1 && data[0].length === 1 && String(data[0][0]).trim() === "";
  if (empty) { appendRowToSheet(sheet,rowData); return; }

  // Tambahkan kolom baru seperti status/riwayat jika spreadsheet berasal dari versi lama.
  var headers = ensureHeaders(sheet,rowData);
  data = sheet.getDataRange().getValues();
  headers = data[0];
  var keyIdx = headers.indexOf(keyField);
  if (keyIdx === -1) { appendRowToSheet(sheet,rowData); return; }

  var targetVal = String(rowData[keyField]), rowIndex=-1;
  for (var i=1; i<data.length; i++) if (String(data[i][keyIdx]) === targetVal) { rowIndex=i+1; break; }

  if (rowIndex > 0) {
    var updated=[];
    for (var j=0; j<headers.length; j++) {
      var val=rowData[headers[j]];
      updated.push(val === undefined || val === null ? (data[rowIndex-1][j] || "") : String(val));
    }
    sheet.getRange(rowIndex,1,1,headers.length).setValues([updated]);
  } else appendRowToSheet(sheet,rowData);
}

function deleteRowInSheet(sheet,keyField,keyValue) {
  var data=sheet.getDataRange().getValues();
  if (data.length<=1) return;
  var keyIdx=data[0].indexOf(keyField);
  if (keyIdx===-1) return;
  for (var i=data.length-1;i>=1;i--) if (String(data[i][keyIdx])===String(keyValue)) { sheet.deleteRow(i+1); break; }
}

function jsonResponse(obj) { return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON); }
