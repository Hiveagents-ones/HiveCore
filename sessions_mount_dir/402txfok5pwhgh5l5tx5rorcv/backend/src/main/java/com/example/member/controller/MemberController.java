package com.example.member.controller;

import com.example.member.entity.Member;
import com.example.member.service.MemberService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/api/v1/members")
public class MemberController {

    private final MemberService memberService;

    @Autowired
    public MemberController(MemberService memberService) {
        this.memberService = memberService;
    }

    /**
     * 创建新会员
     * @param member 会员信息
     * @return 创建的会员
     */
    @PostMapping
    public ResponseEntity<Member> createMember(@RequestBody Member member) {
        Member createdMember = memberService.createMember(member);
        return ResponseEntity.ok(createdMember);
    }

    /**
     * 根据ID查询会员
     * @param id 会员ID
     * @return 会员信息
     */
    @GetMapping("/{id}")
    public ResponseEntity<Member> getMemberById(@PathVariable Long id) {
        Optional<Member> member = memberService.getMemberById(id);
        return member.map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * 根据联系方式查询会员
     * @param contact 联系方式
     * @return 会员信息
     */
    @GetMapping("/contact")
    public ResponseEntity<Member> getMemberByContact(@RequestParam String contact) {
        Optional<Member> member = memberService.getMemberByContact(contact);
        return member.map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * 更新会员信息
     * @param id 会员ID
     * @param memberDetails 更新的会员信息
     * @return 更新后的会员
     */
    @PutMapping("/{id}")
    public ResponseEntity<Member> updateMember(@PathVariable Long id, @RequestBody Member memberDetails) {
        try {
            Member updatedMember = memberService.updateMember(id, memberDetails);
            return ResponseEntity.ok(updatedMember);
        } catch (RuntimeException e) {
            return ResponseEntity.notFound().build();
        }
    }

    /**
     * 删除会员
     * @param id 会员ID
     * @return 无内容
     */
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteMember(@PathVariable Long id) {
        memberService.deleteMember(id);
        return ResponseEntity.noContent().build();
    }

    /**
     * 获取所有会员
     * @return 会员列表
     */
    @GetMapping
    public ResponseEntity<List<Member>> getAllMembers() {
        List<Member> members = memberService.getAllMembers();
        return ResponseEntity.ok(members);
    }

    /**
     * 根据状态查询会员
     * @param status 会员状态
     * @return 会员列表
     */
    @GetMapping("/status")
    public ResponseEntity<List<Member>> getMembersByStatus(@RequestParam Member.MemberStatus status) {
        List<Member> members = memberService.getMembersByStatus(status);
        return ResponseEntity.ok(members);
    }

    /**
     * 根据等级查询会员
     * @param level 会员等级
     * @return 会员列表
     */
    @GetMapping("/level")
    public ResponseEntity<List<Member>> getMembersByLevel(@RequestParam Member.MemberLevel level) {
        List<Member> members = memberService.getMembersByLevel(level);
        return ResponseEntity.ok(members);
    }

    /**
     * 根据姓名模糊查询会员
     * @param name 会员姓名
     * @return 会员列表
     */
    @GetMapping("/search")
    public ResponseEntity<List<Member>> getMembersByNameContaining(@RequestParam String name) {
        List<Member> members = memberService.getMembersByNameContaining(name);
        return ResponseEntity.ok(members);
    }

    /**
     * 获取所有活跃会员
     * @return 活跃会员列表
     */
    @GetMapping("/active")
    public ResponseEntity<List<Member>> getAllActiveMembers() {
        List<Member> members = memberService.getAllActiveMembers();
        return ResponseEntity.ok(members);
    }

    /**
     * 冻结会员
     * @param id 会员ID
     * @return 更新后的会员
     */
    @PutMapping("/{id}/freeze")
    public ResponseEntity<Member> freezeMember(@PathVariable Long id) {
        try {
            Member frozenMember = memberService.freezeMember(id);
            return ResponseEntity.ok(frozenMember);
        } catch (RuntimeException e) {
            return ResponseEntity.notFound().build();
        }
    }
}
