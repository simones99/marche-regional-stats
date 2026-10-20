// Usage: tmdl-check <SemanticModel/definition folder>
// Prints "OK: …" and exits 0 when the folder deserializes, "FAIL: <message>" and exits 1 otherwise.
// It checks the TMDL syntax and object structure, not DAX or Power Query.
using Microsoft.AnalysisServices.Tabular;

try
{
    var model = TmdlSerializer.DeserializeDatabaseFromFolder(args[0]).Model;
    var measures = model.Tables.Sum(t => t.Measures.Count);
    Console.WriteLine(
        $"OK: {model.Tables.Count} tables, {measures} measures, {model.Relationships.Count} relationships"
    );
    return 0;
}
catch (Exception e)
{
    Console.WriteLine("FAIL: " + e.Message);
    return 1;
}
