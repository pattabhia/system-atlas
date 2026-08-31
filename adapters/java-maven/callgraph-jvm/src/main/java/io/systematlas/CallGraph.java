package io.systematlas;

import com.github.javaparser.ParserConfiguration;
import com.github.javaparser.StaticJavaParser;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.body.CallableDeclaration;
import com.github.javaparser.ast.body.ClassOrInterfaceDeclaration;
import com.github.javaparser.ast.body.ConstructorDeclaration;
import com.github.javaparser.ast.body.MethodDeclaration;
import com.github.javaparser.ast.expr.MethodCallExpr;
import com.github.javaparser.resolution.declarations.ResolvedMethodDeclaration;
import com.github.javaparser.resolution.declarations.ResolvedReferenceTypeDeclaration;
import com.github.javaparser.resolution.types.ResolvedReferenceType;
import com.github.javaparser.symbolsolver.JavaSymbolSolver;
import com.github.javaparser.symbolsolver.resolution.typesolvers.CombinedTypeSolver;
import com.github.javaparser.symbolsolver.resolution.typesolvers.JarTypeSolver;
import com.github.javaparser.symbolsolver.resolution.typesolvers.JavaParserTypeSolver;
import com.github.javaparser.symbolsolver.resolution.typesolvers.ReflectionTypeSolver;

import java.io.IOException;
import java.nio.file.*;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Stage B call-graph builder for the java-maven adapter.
 *
 * Resolves each method call to a fully-qualified target via JavaParser +
 * SymbolSolver. Edges are PROVEN (resolved=true) when the solver binds the
 * call to a declaration; UNRESOLVED (resolved=false) otherwise — never guessed.
 *
 * Usage:
 *   java -jar callgraph.jar --src <root>[,<root>...] [--classpath cp.txt]
 * where cp.txt is the output of `mvn dependency:build-classpath` (path list,
 * ':'-separated). Without a classpath, intra-project + JDK calls still resolve;
 * cross-jar calls to unbuilt dependencies resolve to false and are reported.
 *
 * Output: a JSON object on stdout {ok, edges:[...], counts:{...}, errors:[...]}.
 */
public class CallGraph {

    public static void main(String[] args) {
        List<String> srcRoots = new ArrayList<>();
        String classpathFile = null;
        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--src": srcRoots.addAll(Arrays.asList(args[++i].split(","))); break;
                case "--classpath": classpathFile = args[++i]; break;
                default: /* ignore */ break;
            }
        }
        if (srcRoots.isEmpty()) {
            System.out.println("{\"ok\":false,\"error\":\"no_src\",\"remedy\":\"pass --src <root>\"}");
            System.exit(1);
        }

        List<String> errors = new ArrayList<>();
        CombinedTypeSolver solver = new CombinedTypeSolver();
        solver.add(new ReflectionTypeSolver(false)); // JDK
        for (String root : srcRoots) {
            try { solver.add(new JavaParserTypeSolver(Paths.get(root.trim()))); }
            catch (Exception e) { errors.add("src_solver:" + root + ":" + e); }
        }
        int jars = 0;
        if (classpathFile != null) {
            try {
                String cp = Files.readString(Paths.get(classpathFile)).trim();
                for (String entry : cp.split("[:;]")) {
                    if (entry.endsWith(".jar")) {
                        try { solver.add(new JarTypeSolver(entry)); jars++; }
                        catch (Exception e) { errors.add("jar:" + entry + ":" + e); }
                    }
                }
            } catch (IOException e) { errors.add("classpath_read:" + e); }
        }

        ParserConfiguration cfg = new ParserConfiguration()
                .setLanguageLevel(ParserConfiguration.LanguageLevel.JAVA_21)
                .setSymbolResolver(new JavaSymbolSolver(solver));
        StaticJavaParser.setConfiguration(cfg);

        List<String> edges = new ArrayList<>();
        int total = 0, resolved = 0, parseErrs = 0, overrideEdges = 0;

        List<Path> files = new ArrayList<>();
        for (String root : srcRoots) {
            try (var s = Files.walk(Paths.get(root.trim()))) {
                files.addAll(s.filter(p -> p.toString().endsWith(".java"))
                        .filter(p -> !p.toString().contains("/target/"))
                        .collect(Collectors.toList()));
            } catch (IOException e) { errors.add("walk:" + root + ":" + e); }
        }

        // Parse once, keep CUs; build interface/superclass -> concrete-implementor index
        // so calls that resolve to an interface method also emit edges to the overriding
        // implementation(s) (interface->impl dispatch).
        List<CompilationUnit> cus = new ArrayList<>();
        Map<String, List<String>> implsByType = new HashMap<>();   // ancestorQN -> [implQN...]
        Map<String, Set<String>> methodsByType = new HashMap<>();  // typeQN -> {methodName...}
        Set<String> inSourceTypes = new HashSet<>();               // every type DECLARED in the parsed source
        // Pass 1: parse + collect all in-source type QNs (interfaces included) and impl methods.
        for (Path f : files) {
            CompilationUnit cu;
            try { cu = StaticJavaParser.parse(f); }
            catch (Exception e) { parseErrs++; errors.add("parse:" + f + ":" + e.getClass().getSimpleName()); continue; }
            cus.add(cu);
            for (ClassOrInterfaceDeclaration cid : cu.findAll(ClassOrInterfaceDeclaration.class)) {
                String qn;
                try { qn = cid.resolve().getQualifiedName(); } catch (Throwable t) { continue; }
                inSourceTypes.add(qn);
                if (!cid.isInterface()) {
                    Set<String> mnames = methodsByType.computeIfAbsent(qn, k -> new HashSet<>());
                    cid.getMethods().forEach(m -> mnames.add(m.getNameAsString()));
                }
            }
        }
        // Pass 2: index interface/superclass -> concrete impl, keyed on ANY in-source ancestor
        // (generic — no hardcoded project package; a literal would silently break every other codebase).
        for (CompilationUnit cu : cus) {
            for (ClassOrInterfaceDeclaration cid : cu.findAll(ClassOrInterfaceDeclaration.class)) {
                if (cid.isInterface()) continue;
                String implQN;
                try { implQN = cid.resolve().getQualifiedName(); } catch (Throwable t) { continue; }
                try {
                    for (ResolvedReferenceType anc : cid.resolve().getAllAncestors()) {
                        String ancQN = anc.getQualifiedName();
                        if (ancQN != null && inSourceTypes.contains(ancQN))
                            implsByType.computeIfAbsent(ancQN, k -> new ArrayList<>()).add(implQN);
                    }
                } catch (Throwable ignore) { /* unresolved ancestor (external) — skip */ }
            }
        }

        for (CompilationUnit cu : cus) {
            for (MethodCallExpr mce : cu.findAll(MethodCallExpr.class)) {
                total++;
                String caller = enclosing(mce);
                String calleeOwner = null, calleeSig = null;
                boolean isResolved = false;
                try {
                    ResolvedMethodDeclaration rmd = mce.resolve();
                    calleeOwner = rmd.declaringType().getQualifiedName();
                    calleeSig = rmd.getQualifiedSignature();
                    isResolved = true;
                    resolved++;
                    // interface/abstract dispatch: emit override edges to concrete implementors
                    ResolvedReferenceTypeDeclaration dt = rmd.declaringType();
                    boolean abstractish = dt.isInterface() || (rmd.isAbstract());
                    if (abstractish && implsByType.containsKey(calleeOwner)) {
                        String m = mce.getNameAsString();
                        for (String impl : implsByType.get(calleeOwner)) {
                            if (methodsByType.getOrDefault(impl, Set.of()).contains(m)) {
                                edges.add(edgeJson(caller, m, impl, impl + "." + m, true, "override"));
                                overrideEdges++;
                            }
                        }
                    }
                } catch (Throwable t) {
                    calleeOwner = mce.getScope().map(Object::toString).orElse(null);
                }
                edges.add(edgeJson(caller, mce.getNameAsString(), calleeOwner, calleeSig, isResolved, "direct"));
            }
        }

        StringBuilder sb = new StringBuilder();
        sb.append("{\"ok\":true,\"capability\":\"build_call_graph\",")
          .append("\"resolution\":\"javaparser-symbolsolver\",")
          .append("\"edges\":[").append(String.join(",", edges)).append("],")
          .append("\"counts\":{\"edges\":").append(total)
          .append(",\"resolved\":").append(resolved)
          .append(",\"unresolved\":").append(total - resolved)
          .append(",\"override_edges\":").append(overrideEdges)
          .append(",\"files\":").append(files.size())
          .append(",\"parse_errors\":").append(parseErrs)
          .append(",\"classpath_jars\":").append(jars).append("},")
          .append("\"errors\":[").append(errors.stream().map(CallGraph::q).collect(Collectors.joining(","))).append("]}");
        System.out.println(sb);
    }

    private static String enclosing(MethodCallExpr mce) {
        Optional<CallableDeclaration> owner = mce.findAncestor(CallableDeclaration.class);
        if (owner.isEmpty()) return "<top-level>";
        CallableDeclaration<?> cd = owner.get();
        try {
            if (cd instanceof MethodDeclaration md) return md.resolve().getQualifiedSignature();
            if (cd instanceof ConstructorDeclaration ct) return ct.resolve().getQualifiedSignature();
        } catch (Throwable ignore) { /* fall through to a lexical name */ }
        return cd.getNameAsString();
    }

    private static String edgeJson(String caller, String method, String owner, String sig, boolean resolved, String dispatch) {
        return "{\"caller\":" + q(caller) + ",\"callee\":{\"owner_fqn\":" + q(owner)
                + ",\"method\":" + q(method) + ",\"signature\":" + q(sig)
                + "},\"resolved\":" + resolved + ",\"dispatch\":" + q(dispatch) + "}";
    }

    private static String q(String s) {
        if (s == null) return "null";
        StringBuilder b = new StringBuilder("\"");
        for (char c : s.toCharArray()) {
            switch (c) {
                case '"': b.append("\\\""); break;
                case '\\': b.append("\\\\"); break;
                case '\n': b.append("\\n"); break;
                case '\r': b.append("\\r"); break;
                case '\t': b.append("\\t"); break;
                default: b.append(c);
            }
        }
        return b.append("\"").toString();
    }
}
